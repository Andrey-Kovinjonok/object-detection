#!/usr/bin/env python3
import os
import glob
import cv2
import json
from importlib import import_module
from itertools import islice
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, Response, send_from_directory, request, abort

WIDTH = 320
HEIGHT = 240
IMAGE_FOLDER = 'imgs'
load_dotenv('.env')

if os.getenv('CAMERA'):
    Camera = import_module('backend.camera_' + os.environ['CAMERA']).Camera
else:
    print('Default USB camera')
    from backend.camera_opencv import Camera

app = Flask(__name__)


@app.route(os.path.join('/', IMAGE_FOLDER, '<path:filename>'))
def image_preview(filename):
    w = request.args.get('w', None)
    h = request.args.get('h', None)
    date = request.args.get('date', None)

    try:
        im = cv2.imread(os.path.join(IMAGE_FOLDER, filename))
        if w and h:
            w, h = int(w), int(h)
            im = cv2.resize(im, (w, h))
        elif date:
            date = (datetime
                    .strptime(date, "%Y%m%d_%H%M%S")
                    .strftime("%d %b %-H:%M")
                    )
            img_h, img_w = im.shape[:-1]
            cv2.putText(
                    im, "{}".format(date), (0, int(img_h*0.98)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return Response(cv2.imencode('.jpg', im)[1].tobytes(),
                        mimetype='image/jpeg')

    except Exception as e:
        print(e)

    return send_from_directory('.', filename)


@app.route('/api/delete', methods=['POST'])
def delete_image():
    filename = request.form.get('filename', None)
    try:
        os.remove(filename)
        return json.dumps({'status': filename})
    except Exception as e:
        print(e)
        return abort(404)


@app.route('/api/images')
def api_images():
    page = int(request.args.get('page', 0))
    page_size = int(request.args.get('page_size', 16))
    mydate = request.args.get('date', None)
    if mydate is not None:
        mydate = (
                datetime
                .strptime(mydate, "%d/%m/%Y")
                .strftime("%Y%m%d")
                )
        myiter = glob.iglob(os.path.join(IMAGE_FOLDER, '**', mydate, '*.jpg'),
                            recursive=True)
    else:
        myiter = glob.iglob(os.path.join(IMAGE_FOLDER, '**', '*.jpg'),
                            recursive=True)
    start = page * page_size
    end = (page + 1) * page_size
    result = [i for i in islice(myiter, start, end)]
    print('->> Start', start, 'end', end, 'len', len(result))
    return json.dumps(result)


@app.route('/api/single_image')
def single_image():
    detection = bool(request.args.get('detection', False))
    frame = Camera().get_frame()
    if detection:
        frame = Camera().prediction(frame)
    return json.dumps(dict(img=Camera().img_to_base64(frame),
                      width=WIDTH,
                      height=HEIGHT))


@app.route('/')
def status():
    return send_from_directory('../dist', "index.html")


@app.route('/<path:path>')
def build(path):
    return send_from_directory('../dist', path)


if __name__ == '__main__':
    app.run(
            host='0.0.0.0',
            debug=bool(os.getenv('DEBUG')),
            threaded=False,
            port=int(str(os.getenv('PORT')))
            )
