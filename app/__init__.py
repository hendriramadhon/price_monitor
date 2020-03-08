from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import yaml
from datetime import datetime
from flask import json
import os

import time
import atexit

from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

def update_content():
    # scheduler function 

    print("{}: update...".format(time.strftime("%A, %d. %B %Y %I:%M:%S %p")))
    update()

# set scheduler every 3600 seconds(1 hour)
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_content, trigger="interval", seconds=3600)
scheduler.start()
#

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown())

def get_price(url):
    # get the price of the product

    r = requests.get(url)

    soup = BeautifulSoup(r.text)

    vals = {}
    vals = soup.find("input", {'name':'product', 'type':'hidden'})

    id = vals['value']

    vals = soup.find("span", {'id':'product-price-{}'.format(id)})

    return vals['data-price-amount'], id

def get_description(url):
    # get description of the product

    r = requests.get(url)

    soup = BeautifulSoup(r.text)

    vals = {}
    vals = soup.find("section", {'class':'product-info__section product-info__section--desc clearfix'})

    return str(vals)

def get_image(url):
    # get images from url

    r = requests.get(url)

    soup = BeautifulSoup(r.text)

    vals = {}
    vals = soup.find_all("script", {'type':'text/x-magento-init'})

    remove1 = '''<script type="text/x-magento-init">
    {
        "[data-gallery-role=gallery-placeholder]": {
            "mage/gallery/gallery": {
                "mixins":["magnifier/magnify"],
                "magnifierOpts": 
{"fullscreenzoom":"20","top":"","left":"","width":"","height":"","eventType":"hover","enabled":"false"},'''
    remove2 = '''"options"'''
    
    result_img = []
    for i in vals:
        if 'data-gallery-role=gallery-placeholder' in str(i) \
            and 'mage/gallery/gallery' in str(i):
            result = str(i).replace(remove1,'')
            result = result.split(remove2)
            result = result[0].lstrip().rstrip()
            result = result[:-1]
            result = result.replace('"data": [{','')
            result = result.replace('}]','')
            result = result.replace('"','')
            result = result.split(',')

            for r in result:
                if 'jpg' in r:
                    tmp = r.split('https:')
                    tmp2 = 'https:' + tmp[1]
                    tmp2 = tmp2.replace('\\','')
                    result_img.append(tmp2)

    return result_img

@app.route("/page1")
def page1():
    return render_template('page1.html')

@app.route("/page2")
def page2():

    yaml_items = None
    with open('storage/store_file.yaml') as file:
        yaml_items = yaml.load(file, Loader=yaml.FullLoader)
    
    items = []
    for key in list(yaml_items.keys()):

        # get description
        desc = None
        with open('storage/{}_desc.yaml'.format(key),'r', encoding='latin-1') as file:
            desc = file.read()

        items.append({'url':yaml_items[key]['url'], \
            'price':yaml_items[key]['price'], \
                'img':yaml_items[key]['img'], \
                    'desc':desc, \
                        'last_update':yaml_items[key]['last_update']})
        
    
    if items != None:
        return render_template('page2.html', items=items, count=len(items))
    else:
        return "Something Wrong!!!!"


@app.route("/page3", methods=['GET'])
def page3():

    url = request.args.get('urlInput')

    if url != None:
        # get id, price description & image from url
        id, price, desc, img = get_value(url)

        # save to storage
        save(url, id, price, img, desc)

        content = {}

        content[id] = {'url':url, 'price':price, \
                    'last_update':'UTC'+str(datetime.utcnow())
                    }
        
        # get description
        desc = None
        with open('storage/{}_desc.yaml'.format(id),'r', encoding='latin-1') as file:
            desc = file.read()
        content[id]['desc'] = desc

        # construct image tag
        l_img = ""
        for i in img:
            l_img = l_img + "<img src='{}' /><br/>".format(i)
        content[id]['img'] = l_img

        
        return render_template('page3.html', content=content[id])
    else:
        return "Invalid argument!"

def update():
    # update content of yaml file by grabbing again

    items = None
    content = None

    with open('storage/store_file.yaml') as file:
        # read file
        tmp = file.read()

        items = yaml.load(file, Loader=yaml.FullLoader)
        # get data from store_file.yaml

    if items != None:
        content = {}
        for key in list(items.keys()):
            url = items[key]['url']

            id, price, desc, img = get_value(url)

            content[id] = {'url':url, 'price':price, \
                'img':img, 'last_update':'UTC'+str(datetime.utcnow())}

            with open('storage/{}_desc.yaml'.format(id), 'w') as file:
                file.write(desc)
        
    if content != None:
        with open('storage/store_file.yaml', 'w') as file:
            yaml.dump(content, file)


def get_value(url):
    # get content price, id, description, image of url

    price, id = get_price(url)
    desc = get_description(url)
    img = get_image(url)

    return id, price, desc, img

def save(url, id, price, img, desc):
    # save price, id, description, image to yaml and raw file

    list_id = []
    content = {}
    with open('storage/store_file.yaml') as file:
        documents = yaml.load(file, Loader=yaml.FullLoader)

        if documents != None:
            list_id = list(documents.keys())
            content = documents

    if id not in list_id:
        content[id] = {'url':url, 'price':price, \
            'img':img, 'last_update':'UTC'+str(datetime.utcnow())}

        with open('storage/{}_desc.yaml'.format(id), 'w') as file:
            file.write(desc)

    with open('storage/store_file.yaml', 'w') as file:
        yaml.dump(content, file)

    return "price:{}, desc:{}, img:{}, last_update:{}".format(\
        content[id]['price'], \
            desc, \
                content[id]['img'], \
                    content[id]['last_update'])
