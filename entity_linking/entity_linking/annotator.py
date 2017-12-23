from entity_linking.models.Entity import Entity
from entity_linking.models.Candidate import Candidate
from SPARQLWrapper import SPARQLWrapper, JSON
from multiprocessing import Process, Queue
import time
import nltk


def annotate_text(text):
	entities = disambiguate(find_entities(text))
	return format_result_string(text, entities)

def format_result_string(text, entities):
	entities.sort(key=lambda x: x.id)
	result = ""
	index = 0

	for entity in entities:
		url = 'http://en.wikipedia.org/?curid=' + entity.candidates[0].wiki_id
		link = '<a href="' + url + '">' + entity.candidates[0].name.replace('_', ' ') + '</a>'
		entity_mention = entity.name.replace('_', ' ')

		substring_end = text.find(entity_mention, index) + len(entity.name)	
		result += text[index:substring_end].replace(entity_mention, link, 1)
		index = substring_end 

	if index < len(text):
		result += text[index:]

	return result;

def find_entities(text):
    tokens = nltk.word_tokenize(text)
    tagged = nltk.pos_tag(tokens)
    chunked = nltk.ne_chunk(tagged, False)

    # Binary classification
    #entities = [e for e in [retrieve_from_dbpedia('_'.join([y[0] for y in x.leaves()])) for x in chunked.subtrees() if x.label() == "NE"] if e is not None]
    
    # Multiclass classification
    entities = [e for e in [retrieve_from_dbpedia('_'.join([y[0] for y in x.leaves()])) for x in chunked.subtrees() if x.label() in ["PERSON", "ORGANIZATION", "GPE"]] if e is not None]
    
    index = 0
    for entity in entities:
        entity.id = index
        index += 1

    set_neighbors(entities, 4)

    return entities


def retrieve_from_dbpedia(name):
    candidates = {}
    
    while True:
        subjects = send_sparql_request(name, True)
        if (len(subjects["results"]["bindings"]) == 0):
            subjects = send_sparql_request(name, False)
            if (len(subjects["results"]["bindings"]) == 0):
                return None

        prev_cand = ""

        for result in subjects["results"]["bindings"]: 
            this_candidate = result["candidate"]["value"].split("/")[-1]
            
            if (prev_cand != this_candidate):
                prev_cand = this_candidate
                try:
                    candidates[this_candidate] = [result["id"]["value"]] # ([id, subj1, subj2...])          
                except: # No wiki ID
                    candidates.pop(this_candidate, None)
                    continue
   
            try:
                this_category = result["category"]["value"].split("Category:")[-1]
                candidates[this_candidate].append(this_category)
            except: # No attached subjects
                candidates.pop(this_candidate, None)
                continue

        return Entity(name, __make_cand_obj__(candidates, name))
    return None

def __make_cand_obj__(cand_dict, surface_name):
        """Make Candidate objects of all the found candidates"""
        candidates = []
        for candidate, values in cand_dict.items():
            candidates.append(Candidate(candidate, values[1:], 1/len(cand_dict), values[0]))
        return candidates

def send_sparql_request(name, first_try):
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    
    #if (first_try):
    #    sparql.setQuery("""
    #        SELECT * WHERE {
    #            <http://dbpedia.org/resource/""" + name + """_(disambiguation)> dbo:wikiPageDisambiguates ?candidate .
    #            ?candidate dct:subject ?category .
    #            ?candidate dbo:wikiPageID ?id
    #        }
    #        """)
    #else:
    #    sparql.setQuery("""
    #        SELECT * WHERE {
    #            <http://dbpedia.org/resource/""" + name + """> (dbo:wikiPageRedirects)*/(dbo:wikiPageDisambiguates)* ?candidate .
    #            ?candidate dct:subject ?category .
    #            ?candidate dbo:wikiPageID ?id
    #        }
    #        """)


    sparql.setQuery("""
        SELECT * WHERE { 
            {<http://dbpedia.org/resource/""" + name + """_(disambiguation)> dbo:wikiPageDisambiguates ?candidate .
			    ?candidate dct:subject ?category .
                ?candidate dbo:wikiPageID ?id
            }
            UNION
            {<http://dbpedia.org/resource/""" + name + """> (dbo:wikiPageRedirects)*/(dbo:wikiPageDisambiguates)* ?candidate .
                ?candidate dct:subject ?category .
                ?candidate dbo:wikiPageID ?id
            } 
        }""")

    sparql.setReturnFormat(JSON)
    try:
        subjects = sparql.query().convert()
    except:
        subjects = {"results": {
                        "bindings": []
                        }
                   }                    
    return subjects


def set_neighbors(entities, size):
    max_neighbors = len(entities) - 1

    for i in range(0, len(entities)):
        for j in range(1, size + 1):
            
            # Add backward
            if (i-j >= 0 and len(entities[i].neighbors) < max_neighbors and len(entities[i].neighbors) < size):
                entities[i].neighbors.append(entities[i-j])

            # Add forward
            if (i+j < len(entities) and len(entities[i].neighbors) < max_neighbors and len(entities[i].neighbors) < size):
                entities[i].neighbors.append(entities[i+j])
 

def multiple_candidates(entities):
    for e in entities:
        if (len(e.candidates) > 1):
            return True
    return False

def multiproc_scoring(entities, avg_score):   
    queue = Queue()
    jobs = []
    res = []
    
    for i in range(0, len(entities)):
        if (len(entities[i].candidates) > 1):
            p = Process(target=entities[i].calculate_scores, args=(queue, avg_score))
            p.start()
            jobs.append(p)
        else:
            res.append(entities[i])

    for job in jobs:
        res.append(queue.get())

    # Not necessary? 
    for job in jobs:
        job.join()
    
    return res

def update_scores(entities, avg_score, first_iteration=False):
    upd_entities = multiproc_scoring(entities, avg_score)

    # Update neighbors
    for e in upd_entities:
        for neigh in range(0, len(e.neighbors)):
            for other in upd_entities:
                if (other.id == e.neighbors[neigh].id):
                    e.neighbors[neigh] = other
                    break
        
    # Sort entities after winning ratio
    upd_entities.sort(key=lambda x: x.winner_ratio, reverse=True)
    """
    print("-------Iteration---------")
    for e in upd_entities:
        try:
            print(e)
        except:
            print("fuckup")
    """

    # Remove all other candidates for our best bet
    if not first_iteration:
        upd_entities[0].candidates = [upd_entities[0].candidates[0]]
        upd_entities[0].candidates[0].score = 1
        upd_entities[0].winner_ratio = 0
        #print("velger", upd_entities[0].candidates[0].name, "denne runden")
    return upd_entities

def disambiguate(entities, queue=None):
    if len(entities) == 1:
        if entities[0].dbpedia_default != None:
            entities[0].candidates = [entities[0].dbpedia_default]
        else: # Pick candidate with most subjects
            entities[0].candidates = [max(entities[0].candidates, key=lambda x: len(x.subjects))]
            entities[0].candidates[0].score = 1
        return entities

    """
    # Don't remove candidates for first iteration
    if (multiple_candidates(entities)):
        entities = update_scores(entities, False, True)
    """
    
    while (multiple_candidates(entities)):    
        entities = update_scores(entities, False)    
    
    # Add default resources
    for e in entities:
        if (e.dbpedia_default != None and e.dbpedia_default.name != e.candidates[0].name):
            e.candidates.append(e.dbpedia_default)
            for c in e.candidates:
                c.score = 0.5

    while (multiple_candidates(entities)):
        entities = update_scores(entities, True)
    
    """
    if (queue != None):
        queue.put(entities)
        return
    """
    return entities
