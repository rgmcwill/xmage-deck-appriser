import os, json, pprint, requests, time, threading, hashlib
from flask import Flask, flash, request, redirect, url_for, jsonify, render_template, session
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.dirname(os.path.abspath(__file__)) +'/uploads'
BASE_CACHE_PATH = os.path.dirname(os.path.abspath(__file__)) + '/.cache'
ALLOWED_EXTENSIONS = {'dck'}
LAND_KEYWORDS = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp', 'Snow-Covered Mountain', 'Snow-Covered Forest']

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.before_first_request
def activate_job():
    print('starting')

def md5_of_file(path):
    return hashlib.md5(open(path,'rb').read()).hexdigest()

def cache_request(search):
    data = {}

    md5hash = hashlib.md5(search.encode()).hexdigest()
    #If lookup entiry does not exist
    if not os.path.exists(BASE_CACHE_PATH + "/cards/" + md5hash + ".json"):
        print("Making Request !!@!@!")
        response = requests.get('https://api.scryfall.com/cards/search?unique=prints&q=' + search)
        data = response.json()
        # Updates lookup table
        cards = data.get('data')
        if len(cards) > 0:
            # Updates card serch cache
            path = BASE_CACHE_PATH + "/cards/" + md5hash + ".json"
            with open(path, "w") as json_file:
                json.dump(data, json_file)
    else: # Go get the serch results from cache will make a new request if file update is older then 12 hr but not update the lookup table
        path = BASE_CACHE_PATH + "/cards/" + md5hash + ".json"
        # 12 hrs ago
        ago = time.time() - (60*60*12)
        file_modified = os.path.getmtime(path)
        if file_modified < ago:
            print("Making Request !!@!@!12hr!!")
            response = requests.get('https://api.scryfall.com/cards/search?unique=prints&q=' + search)
            data = response.json()
            # Updates card serch cache
            with open(path, "w") as json_file:
                json.dump(data, json_file)
        else:
            print('Loading card from cache')
            with open(path) as json_file:
                data = json.load(json_file)
    # Will return the response either being a request
    return data

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    path = BASE_CACHE_PATH + '/decks/'
    result = {}
    for deck in os.listdir(path):
        if os.path.isfile(path+deck):
            with open(BASE_CACHE_PATH + "/decks/" + deck) as json_file:
                full_deck = json.load(json_file)
            result.update({deck[:-5]:{'deck_name':full_deck.get('deck_name'), 'by_user': full_deck.get('by_user')}})
    return render_template('index.html', result=result)

def proccess_line(line):
    x = 0
    numb = line[x]
    x = x + 1
    while len(line)-1 > x and line[x].isdigit():
        numb = numb + line[x]
        x = x + 1
    
    split_out_card_name = line.split(']')
    string_with_extra_bits = split_out_card_name[len(split_out_card_name)-1]
    string = string_with_extra_bits.strip(' ').strip('\n')
    if LAND_KEYWORDS.count(string) != 0:
        return {}
    return {string:numb}

def proccess_dck(deck_name):
    print(deck_name)
    f = open(UPLOAD_FOLDER + '/' + deck_name, 'r')
    lines = f.readlines()

    main_board_line_cards = {'MB': {}, 'SB': {}}

    for line in lines:
        if line[0].isdigit():
            main_board_line_cards['MB'].update(proccess_line(line))
        elif line[0:2] == 'SB':
            main_line = line.split('SB: ').pop()
            main_board_line_cards['SB'].update(proccess_line(main_line))

    return main_board_line_cards

@app.route('/deck/<deck_hash>')
def deck(deck_hash):
    s = session.get('messages')
    deck = {}
    #When the deck was uploaded it will recomput the deck
    if s != None:
        messages = json.loads(session['messages'])
        #And then write to file
        deck_name=messages.get('deck_name')
        by_user=messages.get('by_user')
        deck = proccess_dck(deck_name)
        deck.update({"deck_name": deck_name, "by_user": by_user})

        with open(BASE_CACHE_PATH + "/decks/" + deck_hash + ".json", "w") as json_file:
            json.dump(deck, json_file)

    #Will read from file
    with open(BASE_CACHE_PATH + "/decks/" + deck_hash + ".json") as json_file:
        deck = json.load(json_file)
    deck_name = deck.get('deck_name')
    by_user = deck.get('by_user')
    flat_deck = {}
    flat_deck.update(deck.get('MB'))
    flat_deck.update(deck.get('SB'))
    # print(temp)
    return render_template('deck.html', result=flat_deck, deck_name=deck_name, by_user=by_user)

@app.route('/price_card')
def price_card():
    card_name = request.args.get('card_name', 0, type=str)
    card_id = request.args.get('card_id', 0, type=str)
    card_price = 0

    dic = cache_request(card_name)
    data = dic.get('data')
    if data == None:
        card_price = -1
    else:
        minPrice = 100000.00
        maxPrice = 0.00
        imageURL = ''
        for card in data:
            prices = card.get('prices')
            price = prices.get('usd')
            if price == None:
                price = prices.get('usd_foil')
            if price != None:
                if float(price) < minPrice:
                    minPrice = float(price)
                    if card.get('card_faces') == None:
                        imageURL = card.get('image_uris').get('normal')
                    else:
                        if card.get('card_faces')[0].get('image_uris') == None:
                            imageURL = card.get('image_uris').get('normal')
                        else:
                            imageURL = card.get('card_faces')[0].get('image_uris').get('normal')
                if float(price) > maxPrice:
                    maxPrice = float(price)

        
        if minPrice == 100000.00 or maxPrice == 0.00:
            card_price = -1
        else:
            card_price = minPrice
    return jsonify(card_name=card_name, card_id=card_id, card_price=card_price, card_image_url=imageURL)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        by_user = request.form.get('by_user')
        # person_name = request.data.by_user
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            data = json.dumps({"by_user":by_user, "deck_name": filename})
            session['messages'] = data
            return redirect(url_for('deck', deck_hash=md5_of_file(UPLOAD_FOLDER+'/'+filename)))
    # print(UPLOAD_FOLDER)
    return render_template('upload.html')

#This is what needs to be stored in the deck.jsons
# - by_user
# - deck_name
# - Commander // Most expencive in deck
# - Price
