"""
Routes and views for the flask application.
"""

from flask import render_template, request
from entity_linking import app
from entity_linking.annotator import annotate_text
import time


@app.route('/')
def home():
    return render_template(
        'index.html',
		input_text = 'Gerrard used to play alongside Carragher for Liverpool'
    )

@app.route('/annotate', methods=['POST'])
def annotate():
	start = time.time()
	text = request.form['text']
	
	return render_template(
		'index.html',
		title = 'Annotated text:',
		input_text = text,
		result = annotate_text(text),
        time = 'Processing time: ' + str(int(time.time() - start)) + ' sec'
	)

