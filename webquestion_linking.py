
# coding: utf-8

# In[1]:

import pickle, spacy

spacy_model = spacy.load('en_core_web_md')
print("Done")

print("Loading Wikidata ID dictionary ... ", end="")
with open("wikidata_table.pickle", "rb") as pickle_jar:
    entity_dict = pickle.load(pickle_jar)
    pickle_jar.close()
print("Done")

print("Loading Wikidata-Freebase Mapping table ... ", end="")
with open("qid-mid.pickle", "rb") as pickle_jar:
    mapping = pickle.load(pickle_jar)
    pickle_jar.close()
print("Done")

expansion_list = []
for entry in entity_dict:
    if entry.replace(".", "") not in entity_dict:
        expansion_list.append((entry.replace(".", ""), entry))
    if entry.replace(",", "") not in entity_dict:
        expansion_list.append((entry.replace(",", ""), entry))

for new, old in expansion_list:
    entity_dict[new] = entity_dict[old]
    
    stopwords = []
with open("stopwords.txt", "r", encoding='utf-8') as t:
    for line in t:
        stopwords.append(line.strip())


# In[39]:

def sense_disamb(qid_list, mapping):
    
    qid_list.sort(key=lambda x : int(x[1:]))
    mid_list = []
    for qid in qid_list:
        if qid in mapping:
            mid_list.append(mapping[qid])
    
    if len(mid_list) == 0:
        return qid_list[0]
    else:
        return mid_list[0]
    
def link_entity(sentence, concept_list, concept_dict):
    sentence = sentence.replace("?", " ?")
    terms = sentence.split()
    pointer = 0
    result_sentence = ""
    for i in range(len(terms)):
        hit_flag = False
        for j in range(len(terms), pointer, -1):
            if terms[pointer] in ["an", "a", "in", "at", "of", "on", "to"]:
                break
                
            candidate_length = len(terms[pointer:j])
            candidate = " ".join(terms[pointer:j])
            if candidate in concept_dict:
                hit_flag = True
                result_sentence += "{" + candidate + ":=:" + concept_dict[candidate] + "}" + " "
                pointer += candidate_length
                break
            else:
                continue
        
        if not hit_flag:
            result_sentence += terms[pointer] + " "
            pointer += 1
        
        if pointer >= len(terms):
            break
    
    return result_sentence

def flat_assertion(sentence):
    
    value = 0
    for i in range(len(sentence)):
        if sentence[i] == "{":
            value += 1
        elif sentence[i] == "}":
            value -= 1
        
        if value != 1 or value != 0:
            return False
        
        return True

def webq_entity(line, debug=False):
    sent = spacy_model(line)
    
    if debug:
        for word in sent:
            print(word.text + "/" + word.pos_, end=" ")
        print()
    
    terms = []
    terms_lemma = []
    all_tokens = []
    all_lemma = []
    obstacles = []
    punct_flag = False
    for word in reversed(sent):
        if word.text in [':', '.', ',']:
            punct_flag = True
            punct = word.text
            continue

        if word.pos_ not in ['VERB', 'PUNCT','DET']:
            if punct_flag:
                terms.append(word.text + punct)
                terms_lemma.append(word.lemma_ + punct)
                all_tokens.append(word.text + punct)
                all_lemma.append(word.lemma_ + punct)
                punct_flag=False
            else:
                terms.append(word.text)
                terms_lemma.append(word.lemma_)
                all_tokens.append(word.text)
        else:
            obstacles.append(word.text)
            all_tokens.append(word.text)

    terms = terms[::-1]
    terms_lemma = terms_lemma[::-1]
    all_tokens = all_tokens[::-1]

    entity_list = []
    for k in range(len(terms)):
        if terms[k] in stopwords:
            continue
        for t in range(len(terms), k, -1):
            candidate = " ".join(terms[k:t])
            candidate_lemma = " ".join(terms_lemma[k:t])
            if candidate in entity_dict:
                entity_id = entity_dict[candidate]
                if type(entity_id) is list:
                    entity_id = sense_disamb(entity_id, mapping)
                try:
                    entity_id = mapping[entity_id]
                except:
                    pass
                entity_list.append((candidate, entity_id))
            elif candidate_lemma in entity_dict:
                entity_id = entity_dict[candidate_lemma]
                if type(entity_id) is list:
                    entity_id = sense_disamb(entity_id, mapping)
                try:
                    entity_id = mapping[entity_id]
                except:
                    pass
                entity_list.append((candidate, entity_id))

    for k in range(len(all_tokens)):
        if all_tokens[k] in stopwords or all_tokens[k] in obstacles:
            continue
        else:
            # Left Search
            for t in range(k):
                candidate = " ".join(all_tokens[t:k+1])
                if candidate in entity_dict:
                    entity_id = entity_dict[candidate]
                    if type(entity_id) is list:
                        entity_id = sense_disamb(entity_id, mapping)
                    try:
                        entity_id = mapping[entity_id]
                    except:
                        pass
                    entity_list.append((candidate, entity_id))
            
            # Right Search
            for t in range(k+1, len(all_tokens)):
                candidate = " ".join(all_tokens[k:t])
                if candidate in entity_dict:
                    entity_id = entity_dict[candidate]
                    if type(entity_id) is list:
                        entity_id = sense_disamb(entity_id, mapping)
                    try:
                        entity_id = mapping[entity_id]
                    except:
                        pass
                    entity_list.append((candidate, entity_id))


    entity_list = list(set(entity_list))
    entity_list.sort(key=lambda x:len(x[0]), reverse=True)
    entity_hash = {}
    
    if debug:
        print(entity_list)

    for entity, mid in entity_list:
        entity_hash[entity] = mid
        
    result = link_entity(line, entity_list, entity_hash)
    return result, entity_list


# In[40]:

files = ["webq.train.questions", "webq.test.questions"]
prefix = "170822.erl."
postfix = ".txt"

for file in files:
    with open(prefix + file + postfix, "w", encoding="utf-8") as g:
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                result, entity_list = webq_entity(line)

                g.write(result + "\n")
                if not flat_assertion:
                    print(result)
        f.close()
        print(file, "finished")
    g.close()
    
print("Done")


# In[58]:

files = ["train_answers", "test_answers"]
prefix = "170822.erl."
postfix = ".txt"

for file in files:
    
    total_cnt = 0
    one_answer = 0
    with open(prefix + file + postfix, "w", encoding="utf-8") as g:
        with open(file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                
                if len(line) == 0:
                    g.write("\n")
                    continue
                
                if "(" in line:
                    line = line[:line.index("(")]
                    
                if line.lower() in entity_dict:
                    result = "{" + line.lower() + ":=:" + str(sense_disamb(entity_dict[line.lower()], mapping)) + "}"
                else:
                    result, entity_list = webq_entity(line)

                g.write(result + "\n")
                if not flat_assertion:
                    print(result)
                
                total_cnt += 1
                if result.count(":=:") == 1 and result[0] == "{" and result[-1] == "}":
                    one_answer += 1
                    
        f.close()
        print(file, "finished", str(one_answer), "/", str(total_cnt))
    g.close()
    
print("Done")