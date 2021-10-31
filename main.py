from flask import Flask, jsonify
import numpy as np
import requests
from pyproj import Proj, transform


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

#if not hosting in the same machine , please change root_url value to the correct url 
root_url = 'http://localhost:8080'

def handle_error(e):
    message = str(e)
    code = 500
    success = False
    response = {
        'success': success,
        'error': {
            'message': message
        }
    }
    return jsonify(response), status_code


@app.route("/api/<string:addresse>", methods=['GET'])
def get(addresse = 'searchedaddress'):
    searchedaddress = addresse
    dataforaddressapi = {
        'q': searchedaddress,
        'limit': 1,
        'autocomplete': 0
    }

    #GET SUGGESTED ADDRESSES
    responseforaddressapi = requests.get('https://api-adresse.data.gouv.fr/search/', params=dataforaddressapi)
    dictionary = responseforaddressapi.json()
    if(len(dictionary.get('features')) <= 0):
        return jsonify({ "success": False, "result": { "message":"No Data Found for This Adress "}}), 404

    adresse1 = dictionary.get('features')[0].get('properties').get('label')

    #CHOOSE FIRST SUGGESTION
    coordinatesarray = dictionary.get('features')[0].get('geometry').get('coordinates')
    array = np.array(coordinatesarray)

    lonvalue = array[0]
    latvalue = array[1]

    #CONVERT COODRINATES TO LAMBERT 93 SYSTEM
    inProj = Proj(init='epsg:4326')
    outProj = Proj(init='epsg:2154')
    x1, y1 = lonvalue,latvalue
    x2, y2 = transform(inProj, outProj, x1, y1)


    #CALLING OUR SERVER
    xml = '''<wfs:GetFeature service='WFS' version='1.1.0'
          xmlns:topp='http://www.openplans.org/topp'
          xmlns:wfs='http://www.opengis.net/wfs'
          xmlns:ogc='http://www.opengis.net/ogc'
          xmlns:gml='http://www.opengis.net/gml'
          xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'
          xsi:schemaLocation='http://www.opengis.net/wfs
                              http://schemas.opengis.net/wfs/1.1.0/wfs.xsd'>
          <wfs:Query typeName='GeoRisqueFR:ExpoArgile_Fxx_L93'>
            <wfs:PropertyName>GeoRisqueFR:ALEA</wfs:PropertyName>
            <wfs:PropertyName>GeoRisqueFR:NIVEAU</wfs:PropertyName>
            <ogc:Filter>
              <ogc:BBOX>
                <ogc:PropertyName>the_geom</ogc:PropertyName>
                <gml:Envelope srsName='http://www.opengis.net/gml/srs/epsg.xml#2154'>
                   <gml:lowerCorner>'''+str(x2)+' '+str(y2)+'''</gml:lowerCorner>
                   <gml:upperCorner>'''+str(x2+0.1)+' '+str(y2+0.1)+'''</gml:upperCorner>
                </gml:Envelope>
              </ogc:BBOX>
           </ogc:Filter>
          </wfs:Query>
        </wfs:GetFeature>
        '''

    #GETTING RESPONSE FROM SERVER
   
    try:  
        returneddata= requests.post(root_url+'/geoserver/wfs?outputFormat=application/json', data=xml).json()
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        handle_error(e)
        
    if len(returneddata.get('features')) > 0:
        ALEA = returneddata.get('features')[0].get('properties').get('ALEA')
        NIV = returneddata.get('features')[0].get('properties').get('NIVEAU')
        return jsonify({ "success": True, "results":{'Address':adresse1,'Alea':ALEA,'Niveau_Alea':NIV, 'AleaLabel': "Exposition au retrait-gonflement des sols argileux : Alea " + ALEA} }), 200
    else:
        return jsonify({'Address':adresse1, 'Alea':"Non",'Niveau_Alea':0, 'AleaLabel': "Exposition au retrait-gonflement des sols argileux : Non"}), 200
#To run the app and make it accessible from all ip adresses 
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


