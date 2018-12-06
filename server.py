import os
from flask import Flask, request, jsonify
from flask_uploads import UploadSet, IMAGES, configure_uploads
from flask_cors import CORS, cross_origin
import pyrebase
import datetime

import gunicorn

# Server Gubbins
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['UPLOADED_IMAGES_DEST'] = './temp/'
images = UploadSet('images', IMAGES)
configure_uploads(app, (images,))

# Firebase Helper
config = {
    "apiKey": "AIzaSyCwqZMITcTwEbTQcWXW5BH2mk4K0jExY6I",
    "authDomain": "backable-5ceed.firebaseapp.com",
    "databaseURL": "https://backable-5ceed.firebaseio.com/",
    "storageBucket": "backable-5ceed.appspot.com",
    "serviceAccount": "./backable-5ceed-firebase-adminsdk-vkvxr-17177b2e9d.json"
}

firebase = pyrebase.initialize_app(config)
db = firebase.database()
storage = firebase.storage()


# API ENDPOINTS
@app.route('/api/v1/new-campaign-submit/', methods=['PUT'])
@cross_origin()
def new_campaign():  # creates new campaign

    creator_name = request.form.get('creator_name')
    title = request.form.get('title')
    description = request.form.get('description')
    goal = request.form.get('goal')
    tags = request.form.get('tags')
    campaign_address = request.form.get('campaign_address')
    campaigner_address = request.form.get('campaigner_address')

    # Saves image in Firebase storage, cleans up temporary files after upload
    filename = images.save(request.files['image'])
    storage.child("images/" + campaign_address + ".jpg").put("temp/" + filename)
    image_url = storage.child("images/" + campaign_address + ".jpg").get_url(1)
    os.remove('temp/' + filename)

    # Creates new campaign in database
    campaign_data = {
        'creator_name': creator_name,
        'title': title,
        'description': description,
        'goal': goal,
        'tags': tags,
        'image_url': image_url,
        'campaigner_address': campaigner_address,
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    db.child("campaigns").child(campaign_address).set(campaign_data)

    # Updates campaigner with new campaign address
    campaigner_data = {'campaign_address': campaign_address}
    db.child("campaigners").child(campaigner_address).push(campaigner_data)

    return 'Campaign {} created by {}.'.format(campaign_address, campaigner_address)


@app.route('/api/v1/get-campaign', methods=['GET'])
@cross_origin()
def get_campaign():
    campaign_address = request.headers.get('campaign_address')
    campaign = db.child("campaigns").child(campaign_address).get()
    return jsonify(campaign.val())


@app.route('/api/v1/get-campaigns', methods=['GET'])
@cross_origin()
def get_campaigns():
    entities = request.headers.get('num_entities')
    print('entities' + entities)
    campaigns = db.child("campaigns").order_by_child('timestamp').limit_to_first(entities).get()
    return jsonify(campaigns.val())


@app.route('/api/v1/submit-new-pledge', methods=['PUT'])
@cross_origin()
def submit_new_pledge():
    campaign_address = request.form.get('campaign_address')
    backer_address = request.form.get('backer_address')
    campaign_data = {'campaign_address': campaign_address}
    db.child("backers").child(backer_address).push(campaign_data)

    return 'Successfully added campaign {} to backer {} profile.'.format(campaign_address, backer_address)


@app.route('/api/v1/remove-pledge', methods=['DELETE'])
@cross_origin()
def remove_pledge():
    backer_address = request.headers.get('backer_address')
    campaign_address = request.headers.get('campaign_address').encode('ascii', 'ignore')
    campaigns = db.child("backers").child(backer_address).get()
    campaigns_dict = campaigns.val()

    fbhash_to_be_removed = ''

    for fbhash in (list(campaigns_dict.keys())):
        if campaigns_dict[fbhash]['campaign_address'] == campaign_address:
            fbhash_to_be_removed = fbhash

    db.child("backers").child(backer_address).child(fbhash_to_be_removed).remove()
    # db.child("backers").child(backer_address).push(campaign_data)
    return 'Removed backer pledge {}'.format(fbhash_to_be_removed)

    # return 'Successfully added campaign {} to backer {} profile.'.format(campaign_address, backer_address)


@app.route('/api/v1/get-campaigns-by-backer', methods=['GET'])
@cross_origin()
def get_campaigns_by_backer():
    backer_address = request.headers.get('backer_address')
    campaigns = db.child("backers").child(backer_address).get()
    return jsonify(campaigns.val())


@app.route('/api/v1/get-campaigner', methods=['GET'])
@cross_origin()
def get_campaigner():
    campaigner_address = request.headers.get('campaigner_address')
    campaigner = db.child("campaigners").child(campaigner_address).get()
    return jsonify(campaigner.val())


@app.route("/")
@cross_origin()
def index():
    return "Welcome to the Backable campaign server. You shouldn't be here!"


if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
