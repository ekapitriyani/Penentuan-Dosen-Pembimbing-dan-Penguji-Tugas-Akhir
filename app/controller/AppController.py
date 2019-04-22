from flask import request, jsonify
from app import app
from app.constant import RequestMethod
from app.model.QueriesModel import Queries
from app.model.DetailsModel import Details
from app.module.Engine import stemmerEN, preprocess, Engine
import pandas as pd
import os


@app.route("/", methods=RequestMethod.GET)
def index():
    return jsonify({"message": "ok"})


@app.route("/search", methods=RequestMethod.GET_POST)
def search():
    dataset = pd.read_excel("app/db/dataset-preprocessed.xlsx")
    if request.method == "GET":
        response = list()  # Define response

        if 'q' in request.args:
            queries = [request.args['q']]
        elif "files" in request.files:
            file = request.files["files"]
            file.save(os.path.join("app/tmp", "queries.xlsx"))
            queries = pd.read_excel("app/tmp/queries.xlsx")
            queries = queries["Queries"].values
        else:
            resp = {
                "error": "invalid request",
                "path": "/search",
                "message": "request should be query or files"
            }
            resp = jsonify(resp)
            resp.status_code = 400
            return resp

        # Preproces queries
        queriesPre = list()
        for query in queries:
            queriesPre.append(preprocess(query))

        # Cek di database apakah ada data dengan query pada inputan ataupun file
        for query in queriesPre:
            data = Queries.findByQueryName(query)
            if data is not None:
                response.append(data)

        if len(response) is not 0:
            return jsonify(response)
        else:
            engine = Engine()
            docs = [str(x) for x in dataset['Preprocessing']]
            documentsName = list()

            for i, doc in enumerate(docs):
                engine.addDocument(doc)
                documentsName.append("Document_{}".format(i + 1))

            for query in queriesPre:
                engine.setQuery(query)  # Set query pencarian

            titlesScores = engine.process_score()
            ScoreDf = (pd.DataFrame(titlesScores)).T
            ScoreDf.columns = queriesPre
            ScoreDf["Documents"] = documentsName
            ScoreDf["Pembimbing"] = dataset["Pembimbing"].values

            dfListed = list()
            for i in queriesPre:
                print(i)
                labels = list()
                for j in ScoreDf[i]:
                    if j > 0.000:
                        labels.append(1)
                    else:
                        labels.append(0)
                datadf = pd.DataFrame(ScoreDf[i])
                datadf["Documents"] = ScoreDf["Documents"]
                datadf["Labels"] = labels
                datadf["Pembimbing"] = ScoreDf["Pembimbing"].values
                dfListed.append(datadf.sort_values(by=[i], ascending=False))

            for i, df in enumerate(dfListed):
                dbQuery = Queries(queriesPre[i])
                for j in range(len(df["Documents"])):
                    document = df["Documents"][j]
                    label = int(df["Labels"][j])
                    score = float(df[queriesPre[i]][j])
                    pembimbing = df["Pembimbing"][j]
                    data = document, label, score, pembimbing
                    details = Details(data)
                    dbQuery.details.append(details)
                dbQuery.save()

            for query in queriesPre:
                data = Queries.findByQueryName(query)
                response.append(data)

            return jsonify(response)


@app.route("/test", methods=RequestMethod.GET)
def getData():
    response = Queries.getAll()
    print(response)
    return jsonify(response)
