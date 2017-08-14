
# coding: utf-8

# In[1]:

import glob, re, os
import spacy, pickle

print("Setting up Enteater [1] Loading Spacy Model ... ", end="")
try:
    spacy_model = spacy.load('en_core_web_md')
    print("Done")
except:
    print("Please install spaCy module first.")
    print("You can download it with the command: 'python -m spacy download en_core_web_md'")
    raise ImportError("spaCy Module is not installed")
    
print("Setting up Enteater [2] Loading Wikidata ID dictionary ... ", end="")
#with open("wikidata_concept2id.pickle", "rb") as pickle_jar:
with open("wikidata_table.pickle", "rb") as pickle_jar:
    entity_dict = pickle.load(pickle_jar)
    pickle_jar.close()
print("Done")

print("Setting up Enteater [3] Loading Wikidata-Freebase Mapping table ... ", end="")
with open("qid-mid.pickle", "rb") as pickle_jar:
    mapping = pickle.load(pickle_jar)
    pickle_jar.close()
print("Done")


# In[158]:

def all_lower(words):
    return words == words.islower()

def is_concept(word):
    return ("{" in word and "}" in word)

def exceptional_bar_split(sentence):
    
    exceptions = ["-the", "-an", "-a", "-their", "-my", "-your", "-his", "-her"]
    result_sentence = []
    terms = split_sentence_with_concepts(sentence)
    for term in terms:
        if "-" in term:
            hit_flag = False
            for ex in exceptions:
                if term[-len(ex):] == ex:
                    result_sentence.append(" - ".join(term.split("-")))
                    hit_flag = True
                    break
            if not hit_flag:
                result_sentence.append(term)
        else:
            result_sentence.append(term)
    
    return " ".join(result_sentence)
        

def bar_merging(sentence):
    
    temp_sentence = ""
    in_concept = False
    for i in range(len(sentence)):
        if sentence[i] == "{":
            in_concept = True
            temp_sentence += sentence[i]
        elif sentence[i] == "}":
            in_concept = False
            temp_sentence += sentence[i]
        elif in_concept and sentence[i] == " ":
            temp_sentence += "_"
        else:
            temp_sentence += sentence[i]
    
    terms = temp_sentence.replace(" - ","-").split()
    for i, term in enumerate(terms):
        if "-" in term and term.count("{") == 1:
            terms[i] = term.replace("{","").replace("}","")
        elif "-" in term and term.count("{") >= 2:
            terms[i] = "{" + term.replace("{","").replace("}","") + "}"
            
    result = " ".join(terms).replace("_", " ")   
    result = exceptional_bar_split(result)
    
    return result

def split_sentence_with_concepts(sentence):
    # Return the segmentation of the sentence regarding to the concepts

    
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
       
    return terms


def plural_to_singular(noun):
    if noun[-3:] == "ies":
        return noun[:-3] + "y"
    elif noun[-2:] == "es":
        return noun[:-2]
    elif noun[-1] == "s":
        return noun[:-1]
    
def remove_punctuation(noun):
    return noun.replace(",", "").replace(".", "").replace("–", "").replace("-", " ").replace(":", " ").replace(";", "")

def deseparate_punctuation(concept):
    return concept.replace(" , ", ", ").replace(" . ", ". ").replace(" : ", ": ").replace(" ; ", "; ")

def reseparate_punctuation(concept):
    return concept.replace(", ", " , ").replace(". ", " . ").replace(": ", " : ").replace("; ", " ; ")

def get_QID(concept):
    
    concept = deseparate_punctuation(concept.lower())
    lemma_concept = []
    for word in spacy_model(concept):
        lemma_concept.append(word.lemma_)
    lemma_concept = " ".join(lemma_concept)
    
    if concept in entity_dict:
        qid_list = entity_dict[concept]
    elif remove_punctuation(concept) in entity_dict:
        qid_list = entity_dict[remove_punctuation(concept)]
    elif lemma_concept in entity_dict:
        qid_list = entity_dict[lemma_concept]
    elif concept.replace("-","–") in entity_dict:
        qid_list = entity_dict[concept.replace("-","–")]
    else:
        return 'None'

    qid_list.sort(key=lambda x: int(x[1:]))
    for qid in qid_list:
        if qid in mapping:
            return qid
        
    return qid_list[0]

def is_in_entity_dict(concept):
    concept = concept.lower()
    lemma_concept = []
    for word in spacy_model(concept):
        lemma_concept.append(word.lemma_)
    lemma_concept = " ".join(lemma_concept)
    
    if concept in entity_dict or remove_punctuation(concept) in entity_dict or lemma_concept in entity_dict or concept.replace("-","–") in entity_dict:
        return True
    return False

def lemmatize_sentence(sentence):
    
    terms = sentence.split()
    concept_start_position = []
    concept_end_position = []
    for i, term in enumerate(terms):
        if "{" in term:
            concept_start_position.append(i)
        if "}" in term:
            concept_end_position.append(i)
            
    result = []
    for word in spacy_model(sentence.replace("{","").replace("}","")):
        result.append(word.lemma_)
    
    for i in concept_start_position:
        result[i] = "{" + result[i]
    for i in concept_end_position:
        result[i] = result[i] + "}"
    result = " ".join(result)
    
    return result

def remove_brackets(concept):
    return concept.replace("{","").replace("}","")


# In[192]:

def Initial_anchor_noun_establishment(sentence, debug=False):
    glue_word = ['that', 'what', 'whom', 'which', 'where', 'whose', 'who', 'when', 'her', 'his', 'their', 'many', 'much',
                 'That', 'What', 'Whom''Which', 'Where', 'Whose', 'Who', 'When', 'Her', 'His', 'Their', 'Many', 'Much'] 
    token_char = ["[", "]", "{", "}"]
    for char in token_char:
        sentence = sentence.replace(char, "")
    sentence = sentence.replace("–", "-")
    
    sent = spacy_model(sentence)
    if debug:
        print()
        print("[DEBUG] Sentence POS-tagging result ")
        for word in sent:
            print(str(word.text) + "/" + str(word.pos_) + " ", end="")
        print("\n", end="")
            
    result_sent = ""
    slash_flag = False
    for i, word in enumerate(sent):
        if (word.pos_ == 'NOUN' or word.pos_ == 'PROPN' or word.pos_ == 'NUM' or word.pos_== 'PART') and word.text not in glue_word:
            if word.pos_ == 'NOUN':
                result_sent += "{N:" + word.text +":N}"
            elif word.pos_ == 'PROPN':
                result_sent += "{P:" + word.text +":P}"
            elif word.pos_ == 'NUM' and not word.text.isdigit():
                if word.text == 'one':
                    result_sent += word.text
                else:
                    result_sent += "{X:" + word.text +":X}"
            elif word.pos_ == 'PART' and word.text == "'s":
                result_sent += "{S:" + word.text +":S}"
            else:
                result_sent += word.text
            
        elif (word.pos_ == 'ADJ' and word.text[0].isupper()) and word.text not in glue_word:
            result_sent += "{A:" + word.text +":A}"
        else:
            result_sent += word.text
        result_sent += " "
        
    if debug:
        print()
        print("[DEBUG] Initial anchor noun establishment ")
        print(result_sent)
    
    result_sent = result_sent.replace(":S} {S:", " ")
    result_sent = result_sent.replace(":P} {P:", " ")
    result_sent = result_sent.replace(":X} {X:", " ")
    result_sent = result_sent.replace(":N} {X:", " ")
    result_sent = result_sent.replace(":P} {X:", " ")
    result_sent = result_sent.replace(":X} {P:", " ")
    result_sent = result_sent.replace(":P} {S:", " ")
    result_sent = result_sent.replace(":S} {P:", " ")
    result_sent = result_sent.replace(":P} {S:", " ")
    result_sent = result_sent.replace(":S} {P:", " ")
    
    result_sent = result_sent.replace("{N:", "{").replace(":N}", "}").replace("{P:", "{").replace(":P}", "}")
    result_sent = result_sent.replace("{X:", "{").replace(":X}", "}").replace("{A:", "{").replace(":A}", "}")
    result_sent = result_sent.replace("{S:", "{").replace(":S}", "}")
    
    result_sent = bar_merging(result_sent)
    
    if debug:
        print()
        print("[DEBUG] After initial merging ")
        print(result_sent)
    
    return result_sent

def concept_expand(concept_list, sentence, debug):
    stop_words = [".", ":", ";", ",", "\"", "'", "?", "!", "an", "a", "the", "and", "or"]
    
    terms = split_sentence_with_concepts(sentence)
    lemma_sentence = lemmatize_sentence(sentence)
    lemma_terms = split_sentence_with_concepts(lemma_sentence)
    
    #If the first word is an article, ignore it
    if terms[0] in ['A', 'An', 'The']:
        terms = terms[1:]
    
    if debug:
        print()
        print("[DEBUG] Before expanding the concepts ")
        print(concept_list)
    
    # Every concept in the concept_list will be expanded and examined both left and right direction
    # Left expansion : spain {flu} -> {spain flu}
    # Right expansion : {spain} flu -> {spain flu}
    for i, term in enumerate(terms):
        if is_concept(term): 
            # Left Expansion
            for j in range(1,len(terms)):
                if i-j < 0 or (is_concept(terms[i-j]) and abs(i-j) > 5) or (terms[i-j] in stop_words and all_lower(terms[i-j])):
                    break
                else:
                    candidate_concept = " ".join(terms[i-j:i]) + " "+ remove_brackets(term)
                    candidate_concept = remove_brackets(candidate_concept)
                    candidate_concept = deseparate_punctuation(candidate_concept)
                    if is_in_entity_dict(candidate_concept):
                        concept_list.append((reseparate_punctuation(candidate_concept), "Hit"))
                    
            # Right Expansion
            for j in range(i+1,len(terms)):
                if (is_concept(terms[j]) and abs(i-j) > 5) or (terms[j] in stop_words and all_lower(terms[j])):
                    break
                else:
                    candidate_concept = remove_brackets(term) + " " + " ".join(terms[i+1:j+1])
                    candidate_concept = remove_brackets(candidate_concept)
                    candidate_concept = deseparate_punctuation(candidate_concept)
                    if is_in_entity_dict(candidate_concept):
                        concept_list.append((reseparate_punctuation(candidate_concept), "Hit"))
            
            # Left and Right Expansion ( greedily collect upper-case words )
            candidate_concept = []
            for j in range(1, len(terms)):
                if i-j < 0 or is_concept(terms[i-j]) or all_lower(terms[i-j]) or terms[i-j] in stop_words:
                    break
                else:
                    candidate_concept.append(terms[i-j])
            candidate_concept = candidate_concept[::-1]
            candidate_concept.append(remove_brackets(term))
            for j in range(i+1, len(terms)):
                if is_concept(terms[j]) or all_lower(terms[j]) or terms[j] in stop_words:
                    break
                else:
                    candidate_concept.append(terms[j])
            candidate_concept = " ".join(candidate_concept)
            if is_in_entity_dict(candidate_concept):
                concept_list.append((reseparate_punctuation(candidate_concept), "Hit"))
            
                        
    if debug:
        print()
        print("[DEBUG] After the Left-Right Concept Expansion")
        print(concept_list)
                
    
    # Inter-concepts Expansion
    # {University} of {California} -> {University of California}
    concept_location = []
    for i,term in enumerate(terms):
        if is_concept(term):
            concept_location.append(i)
    
    for i in range(len(concept_location)):
        for j in range(i+1, len(concept_location)):
            candidate_concept = remove_brackets(" ".join(terms[concept_location[i]:concept_location[j]+1]))
            candidate_concept = deseparate_punctuation(candidate_concept)
            if is_in_entity_dict(candidate_concept):
                concept_list.append((reseparate_punctuation(candidate_concept), "Hit"))
            
            lemma_candidate_concept = remove_brackets(" ".join(lemma_terms[concept_location[i]:concept_location[j]+1]))
            lemma_candidate_concept = deseparate_punctuation(lemma_candidate_concept)
            if is_in_entity_dict(lemma_candidate_concept):
                concept_list.append((reseparate_punctuation(candidate_concept), "Hit"))
    
        
    concept_list = list(set(concept_list))
    concept_list.sort(key=lambda x : -len(x[0]))
    
    if debug:
        print()
        print("[DEBUG] After the Inter-concepts Concept Expansion")
        print(concept_list)
    
    return concept_list

def retrieve_entity(sentence, use_freebase=False, debug=False, no_None=False, detect_property=True):

    lemma_sentence = lemmatize_sentence(sentence)
    terms = split_sentence_with_concepts(sentence)
    lemma_terms = split_sentence_with_concepts(lemma_sentence)
    
    # Construct concept dictionary
    concept_dict = {}
    for i, term in enumerate(terms):
        if is_concept(term):
            original_term = remove_brackets(term)
            concept = remove_brackets(term).lower()
            concept_lemma = remove_brackets(lemma_terms[i]).lower()

            if concept in entity_dict or concept_lemma in entity_dict:
                concept_dict[original_term] = "Hit"
            else:
                concept_dict[original_term] = "None"

    # Construct concept list
    concept_list = []
    for concept in concept_dict:
        if not (concept_dict[concept] == 'None' and all_lower(concept)):
            if not (no_None and concept_dict[concept] == 'None'):
                concept_list.append((concept, concept_dict[concept]))
    concept_list = list(set(concept_list))
    
    # Expand the concept list ( apply it twice)
    concept_list = concept_expand(concept_list, sentence, debug)
    
    # Assign Entity QID to the concept_list and concept_dictionary
    concept_list_with_QID = []
    for concept,_ in concept_list:
        qid = get_QID(concept)
        concept_list_with_QID.append((concept, qid))
        concept_dict[concept] = qid
    
    if debug:
        print()
        print("[DEBUG] Concept list after sorting by length")
        print(concept_list)
    
    return concept_list, concept_dict

def link_entity(sentence, concept_list, concept_dict, use_freebase, debug, no_None, detect_property, append_id=True):
    
    if debug:
        print()
        print("[DEBUG] Before linking entity ")
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
        print()
        print("[DEBUG] After linking entity ")
        print(result_sentence)
        
    return result_sentence


# In[168]:


def find_entity(sentence, use_freebase=False, debug=False, no_None=False, detect_property=True):
    
    result_sent = Initial_anchor_noun_establishment(sentence, debug)
    concept_list, concept_dict = retrieve_entity(result_sent, use_freebase, debug, no_None, detect_property)
    result_sent = link_entity(result_sent, concept_list, concept_dict, use_freebase, debug, no_None, detect_property)
    
    return result_sent

def get_entity(sentence, use_freebase=False, debug=False, no_None=False, detect_property=True):
    
    result_sent = Initial_anchor_noun_establishment(sentence, debug)
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

def test():
    with open("test_sentence.txt", "r", encoding="utf-8") as f:
        for line in f:
            print(find_entity(line))
            print()

