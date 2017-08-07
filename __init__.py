
# coding: utf-8

# In[1]:

import glob, re, os
import spacy, pickle

def result_post_processing(sentence, debug):
    result = sentence.replace("} {", " ")
    if debug:
        print(result)
    return result

def all_lower(words):
    return words == words.islower()

def is_concept(word):
    return ("{" in word and "}" in word)

def concept_expand(concept_list, sentence):
    stop_words = [".", ":", ";", ",", "\"", "'", "?", "!", "an", "a", "the", "and", "or"]
    _terms = sentence.split()
    
    concept_flag = False
    terms = []
    for term in _terms:
        if not concept_flag and "{" not in term and "}" not in term:
            terms.append(term)
            
        elif not concept_flag and ("{" in term and "}" in term):
            terms.append(term)

        elif "{" in term:
            concept_flag = True
            concept_amalgamation = [term]

        elif concept_flag and "{" not in term and "}" not in term:
            concept_amalgamation.append(term)

        elif concept_flag and "}" in term:
            concept_flag = False
            concept_amalgamation.append(term)
            terms.append(" ".join(concept_amalgamation))
    
    if terms[0] in ['A', 'An', 'The']:
        terms = terms[1:]
    
    for i, term in enumerate(terms):
        if is_concept(term): 
            # Left search
            for j in range(1,len(terms)):
                if i-j < 0 or is_concept(terms[i-j]) or terms[i-j] in stop_words:
                    break
                else:
                    candidate_concept = " ".join(terms[i-j:i]) + " "+ term.replace("{","").replace("}","")

                    if candidate_concept.lower() in entity_dict:
                        if type(entity_dict[candidate_concept.lower()]) is list:
                            concept_list.append((candidate_concept, entity_dict[candidate_concept.lower()][0]))
                        else:
                            concept_list.append((candidate_concept, entity_dict[candidate_concept.lower()]))
            # Right search
            for j in range(1,len(terms)):
                if i+j+1 > len(terms)-1 or is_concept(terms[i+j]) or terms[i+j] in stop_words:
                    break
                else:
                    candidate_concept = term.replace("{","").replace("}","") + " " + " ".join(terms[i+1:i+j+1])
                    if candidate_concept.lower() in entity_dict:
                        if type(entity_dict[candidate_concept.lower()]) is list:
                            concept_list.append((candidate_concept, entity_dict[candidate_concept.lower()][0]))
                        else:
                            concept_list.append((candidate_concept, entity_dict[candidate_concept.lower()]))
    
    concept_location = []
    for i,term in enumerate(terms):
        if is_concept(term):
            concept_location.append(i)
    
    for i in range(len(concept_location)):
        for j in range(i+1, len(concept_location)):
            candidate_concept = " ".join(terms[concept_location[i]:concept_location[j]+1]).replace("{", "").replace("}","")
            if candidate_concept.lower() in entity_dict:
                if type(entity_dict[candidate_concept.lower()]) is list:
                    if entity_dict[candidate_concept.lower()][0] in mapping:
                        concept_list.append((candidate_concept, entity_dict[candidate_concept.lower()][0]))
                else:
                    if entity_dict[candidate_concept.lower()] in mapping:
                        concept_list.append((candidate_concept, entity_dict[candidate_concept.lower()]))
        
                        
    return concept_list

def retrieve_entity(sentence, use_freebase=False, debug=False, no_None=False, detect_property=True):
    concept_index_list = [ (int(m.start(0))+1, int(m.end(0))-1) for m in re.finditer("\{(.+?)\}", sentence) ]
    concept_num = len(concept_index_list)
    
    concept_dict = {}
    for concept_index in concept_index_list:    
        concept = sentence[concept_index[0]:concept_index[1]].replace("{", "").replace("}", "")
        concept_lemma = spacy_model(concept)[0].lemma_
        
        if concept.lower() in entity_dict:
            wid = min(entity_dict[concept.lower()], key=lambda x: int(x[1:]))
            concept_dict[concept] = wid
        elif len(concept.split()) == 1 and concept_lemma.lower() in entity_dict:
            wid = min(entity_dict[concept_lemma.lower()], key=lambda x: int(x[1:]))
            concept_dict[concept] = wid
        else:
            concept_dict[concept] = "None"
    
    if debug:
        print(concept_dict)
    
    concept_list = []
    for concept in concept_dict:
        if not (concept_dict[concept] == 'None' and all_lower(concept)):
            if not (no_None and concept_dict[concept] == 'None'):
                concept_list.append((concept, concept_dict[concept]))
    
    concept_list = list(set(concept_list))
    concept_list = concept_expand(concept_list, sentence)
    concept_list.sort(key=lambda x : -len(x[0]))
    
    for concept, qid in concept_list:
        concept_dict[concept] = qid
    
    if debug:
        print(concept_list)
    
    return concept_list, concept_dict

def link_entity(sentence, use_freebase, debug, no_None, detect_property):
    
    concept_list, concept_dict = retrieve_entity(sentence, use_freebase, debug, no_None, detect_property)
    
    if debug:
        print(sentence)
    
    raw_sentence = sentence.replace("{","").replace("}","")

    pointer = 0
    result_sentence = ""
    hit_flag = False
    for i in range(len(raw_sentence)):
        if i < pointer:
            continue
        else:
            hit_flag = False
            for concept in concept_list:
                candidate = raw_sentence[i:i+len(concept[0])]
                if candidate in concept_dict:
                    concept_id = concept_dict[raw_sentence[i:i+len(concept[0])]]
                    if concept_id[0] != 'P' or detect_property:
                        if use_freebase:
                            if concept_id in mapping:
                                concept_id = mapping[concept_id]

                        concept_length = len(concept[0])
                        for k in range(100):
                            concept_length += 1
                            if not raw_sentence[i:i+concept_length].isalnum():
                                concept_length -= 1
                                break

                        result_sentence += ("{" + raw_sentence[i:i+concept_length].replace(" ","_") + ":=:"+ str(concept_id) + "}")
                        pointer += concept_length
                        hit_flag = True
                        break
            if not hit_flag:
                pointer += 1
                result_sentence += raw_sentence[i]
    
    if debug:
        print(result_sentence)
        
    return result_sentence
def bar_handling(sentence, debug):
    terms = sentence.replace(" - ","-").split()
    for i, term in enumerate(terms):
        if "-" in term and term.count("{") == 1:
            terms[i] = term.replace("{","").replace("}","")
        elif "-" in term and term.count("{") >= 2:
            terms[i] = "{" + term.replace("{","").replace("}","") + "}"
            
    result = " ".join(terms)
    if debug:
        print(result)
    return result
            
def sentence_preprocessing(sentence, debug=False):
    glue_word = ['that', 'what', 'which', 'where', 'whose', 'who', 'when', 'her', 'his', 'their', 'many', 'much'] 
    token_char = ["[", "]", "{", "}"]
    for char in token_char:
        sentence = sentence.replace(char, "")
    
    sent = spacy_model(sentence)
    if debug:
        for word in sent:
            print(str(word.text) + "/" + str(word.pos_) + " ", end="")
        print("\n")
            
    result_sent = ""
    slash_flag = False
    for i, word in enumerate(sent):
        if (word.pos_ == 'NOUN' or word.pos_ == 'PROPN') and word.text not in glue_word:
            result_sent += "{" + word.text +"}"
        elif (word.pos_ == 'ADJ' and word.text[0].isupper()) and word.text not in glue_word:
            result_sent += "[" + word.text +"]"
        else:
            result_sent += word.text
        result_sent += " "
    
    if debug:
        print(result_sent)
    
    return result_sent

def find_entity(sentence, use_freebase=False, debug=False, no_None=False, detect_property=True):
    
    result_sent = sentence_preprocessing(sentence, debug)
    result_sent = bar_handling(result_sent, debug)
    result_sent = result_post_processing(result_sent, debug)
    result_sent = result_sent.replace("[", "{").replace("]", "}")
    result_sent = link_entity(result_sent, use_freebase, debug, no_None, detect_property)
    
    return result_sent

def get_entity(sentence, use_freebase=False, debug=False, no_None=False, detect_property=True):
    result_sent = sentence_preprocessing(sentence, debug)
    result_sent = bar_handling(result_sent, debug)
    result_sent = result_post_processing(result_sent, debug)
    result_sent = result_sent.replace("[", "{").replace("]", "}")
    concept_list, concept_dict = retrieve_entity(result_sent, use_freebase, debug, no_None, detect_property)
    
    return concept_list, concept_dict

def get_wikidata_id(_entity):
    entity = _entity.lower()
    if entity in entity_dict:
        return entity_dict[entity]
    else:
        return "None"

def get_freebase_id(_entity):
    entity = _entity.lower()
    if entity in entity_dict:
        if type(entity_dict[entity]) is list:
            entity_id = entity_dict[entity][0]
        else:
            entity_id = entity_dict[entity]
            
        if entity_id in mapping:
            return mapping[entity_id]
    return "None"
    
print("Setting up Enteater [1] Loading Spacy Model ... ", end="")
try:
    spacy_model = spacy.load('en_core_web_md')
    print("Done")
except:
    print("Please install spaCy module first.")
    print("You can download it with the command: 'python -m spacy download en_core_web_md'")
    raise ImportError("spaCy Module is not installed")
    
print("Setting up Enteater [2] Loading Wikidata ID dictionary ... ", end="")
with open("enteater/wikidata_concept2id.pickle", "rb") as pickle_jar:
    entity_dict = pickle.load(pickle_jar)
    pickle_jar.close()
print("Done")

print("Setting up Enteater [3] Loading Wikidata-Freebase Mapping table ... ", end="")
with open("enteater/qid-mid.pickle", "rb") as pickle_jar:
    mapping = pickle.load(pickle_jar)
    pickle_jar.close()
print("Done")


# In[ ]:



