import os, json, pprint, requests, time
from flask import Flask, flash, request, redirect, url_for
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = '/home/svfserver/XDA/uploads'
ALLOWED_EXTENSIONS = {'dck'}
LAND_KEYWORDS = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp', 'Snow-Covered Mountain', 'Snow-Covered Forest']

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
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
            return redirect(url_for('deck', deck_name=filename))
    return '''
    <!doctype html>
    <title>XDA</title>
    <h1>Upload a .dck file for appraising</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''

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

@app.route('/deck/<deck_name>')
def deck(deck_name):
    a = proccess_dck(deck_name)
    cost = 0
    for k,v in a['MB'].items():
        response = requests.get('https://api.scryfall.com/cards/search?q=' + k)
        dic = response.json()
        print(response.status_code)
        b = dic['data'][0]['prices']['usd']
        if b != None:
            card_cost  = float(b)
            cost = cost + card_cost
        time.sleep(0.75)
    for k,v in a['SB'].items():
        response = requests.get('https://api.scryfall.com/cards/search?q=' + k)
        dic = response.json()
        print(response.status_code)
        b = dic['data'][0]['prices']['usd']
        if b != None:
            card_cost  = float(b)
            cost = cost + card_cost
        time.sleep(0.75)
    to_return = str(a) + '<div></div>' + str(cost)
    return to_return
