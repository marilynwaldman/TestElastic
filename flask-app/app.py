from elasticsearch import Elasticsearch, exceptions
import os
import time
from flask import Flask, jsonify, request, render_template
import sys
import requests
import simplejson as json


es = Elasticsearch(host='http://ec2-34-221-143-38.us-west-2.compute.amazonaws.com')

app = Flask(__name__)

def load_data_in_es():
    """ creates an index in elasticsearch """
    #url = "http://data.sfgov.org/resource/rqzj-sfat.json"
    url = "https://services3.arcgis.com/66aUo8zsujfVXRIT/arcgis/rest/services/Community_Testing_Sites/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=json"
    r = requests.get(url)
    data = r.json()
    print("Loading data in elasticsearch ...")
    for id, site in enumerate(data['features']):
        res = es.index(index="codata", doc_type="site", id=id, body=site['attributes'])
    print("Total trucks loaded: ", len(data))

def safe_check_index(index, retry=3):
    """ connect to ES with retry """
    if not retry:
        print("Out of retries. Bailing out...")
        sys.exit(1)
    try:
        status = es.indices.exists(index)
        return status
    except exceptions.ConnectionError as e:
        print("Unable to connect to ES. Retrying in 5 secs...")
        time.sleep(5)
        safe_check_index(index, retry-1)

def format_fooditems(string):
    items = [x.strip().lower() for x in string.split(":")]
    return items[1:] if items[0].find("cold truck") > -1 else items

def check_and_load_index():
    """ checks if index exits and loads the data accordingly """
    if not safe_check_index('codata'):
        print("Index not found...")
        load_data_in_es()

def testsearch(uri):
  """Simple Elasticsearch Query"""
  query = json.dumps({
    "query": {
      "match": {
        "STATE": "CO"
      }
    }
  })
  response = requests.get(uri,   headers={"Content-type":"application/json"}, data=query)
  results = json.loads(response.text)
  print(results)
  return results


###########
### APP ###
###########
"""
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/debug')
def test_es():
    resp = {}
    try:
        msg = es.cat.indices()
        resp["msg"] = msg
        resp["status"] = "success"
    except:
        resp["status"] = "failure"
        resp["msg"] = "Unable to reach ES"
    return jsonify(resp)

@app.route('/search')
def search():
    key = request.args.get('q')
    if not key:
        return jsonify({
            "status": "failure",
            "msg": "Please provide a query"
        })
    try:
        res = es.search(
                index="sfdata",
                body={
                    "query": {"match": {"fooditems": key}},
                    "size": 750 # max document size
              })
    except Exception as e:
        return jsonify({
            "status": "failure",
            "msg": "error in reaching elasticsearch"
        })
    # filtering results
    vendors = set([x["_source"]["applicant"] for x in res["hits"]["hits"]])
    temp = {v: [] for v in vendors}
    fooditems = {v: "" for v in vendors}
    for r in res["hits"]["hits"]:
        applicant = r["_source"]["applicant"]
        if "location" in r["_source"]:
            truck = {
                "hours"    : r["_source"].get("dayshours", "NA"),
                "schedule" : r["_source"].get("schedule", "NA"),
                "address"  : r["_source"].get("address", "NA"),
                "location" : r["_source"]["location"]
            }
            fooditems[applicant] = r["_source"]["fooditems"]
            temp[applicant].append(truck)

    # building up results
    results = {"trucks": []}
    for v in temp:
        results["trucks"].append({
            "name": v,
            "fooditems": format_fooditems(fooditems[v]),
            "branches": temp[v],
            "drinks": fooditems[v].find("COLD TRUCK") > -1
        })
    hits = len(results["trucks"])
    locations = sum([len(r["branches"]) for r in results["trucks"]])

    return jsonify({
        "trucks": results["trucks"],
        "hits": hits,
        "locations": locations,
        "status": "success"
    })
"""
if __name__ == "__main__":

    uri_search = 'http://ec2-54-214-200-23.us-west-2.compute.amazonaws.com:9200/codata/_search'
    ENVIRONMENT_DEBUG = os.environ.get("DEBUG", False)
    #check_and_load_index()
    testsearch(uri_search)
    #app.run(host='0.0.0.0', port=5000, debug=ENVIRONMENT_DEBUG)
