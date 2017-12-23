from entity_linking.models.Candidate import Candidate
#from multiprocessing import Process, Queue
from math import pow


class Entity:
   
    def __init__(self, name, candidates):
        self.name = name    # string
        self.neighbors = [] # list
        self.candidates = candidates    # list
        self.winner_ratio = 0
        self.num_cands = len(candidates)     
        self.id = -1
        
        self.dbpedia_default = None
        for c in candidates:
            if self.name == c.name:
                self.dbpedia_default = c
                break
       
         
    def calculate_scores(self, queue, avg_score):  
        cand = 0
        
        while cand < len(self.candidates):
            self.candidates[cand].score = 0 # Reset for this iteration

            for n_entity in range(0, len(self.neighbors)):            
                
                for n_cand in range(0, len(self.neighbors[n_entity].candidates)):
                    cand_pair = 0.0        

                    # Compare subjects of the two candidates           
                    for subj in range(0, len(self.candidates[cand].subjects)):                         
                        for n_subj in range(0, len(self.neighbors[n_entity].candidates[n_cand].subjects)):
                            subj_pair = self.__longest_common_substring__(self.candidates[cand].subjects[subj], self.neighbors[n_entity].candidates[n_cand].subjects[n_subj]) 
                            cand_pair += subj_pair
                    self.candidates[cand].score += (cand_pair * self.neighbors[n_entity].candidates[n_cand].score)

            if (avg_score):
                self.candidates[cand].score /= len(self.candidates[cand].subjects)
            
            cand += 1
        
        self.__scale_scores__()

        self.candidates.sort(key=lambda x: x.score, reverse=True)
        self.candidates = [c for c in self.candidates if c.score > self.candidates[0].score/2]

        if (len(self.candidates) > 1):
            self.winner_ratio = self.candidates[0].score / self.candidates[1].score
        else:
#            print("velger", self.candidates[0].name, "fordi den er overlegen")
            self.candidates[0].score = 1
            
        queue.put(self)   
    
    '''
    def __multiproc_candidate_scoring__(self, candidate, cand_queue, avg_score):
        candidate.score = 0 # Reset for this iteration
        
        for n_entity in range(0, len(self.neighbors)):
            #print(self.neighbors[n_entity].name, len(self.neighbors[n_entity].candidates))
            for n_cand in range(0, len(self.neighbors[n_entity].candidates)):
                cand_pair = 0.0
                # Compare subjects of the two candidates
                for subj in range(0, len(candidate.subjects)):
                    for n_subj in range(0, len(self.neighbors[n_entity].candidates[n_cand].subjects)):
                        subj_pair = self.__longest_common_substring__(candidate.subjects[subj], self.neighbors[n_entity].candidates[n_cand].subjects[n_subj])
                        cand_pair += subj_pair
                candidate.score += (cand_pair * self.neighbors[n_entity].candidates[n_cand].score)

        if (avg_score):
            candidate.score /= len(candidate.subjects)

        cand_queue.put(candidate)

    
    def calculate_scores(self, entity_queue, avg_score):             
        cand_queue = Queue()
        jobs = []
        res = []

        for cand in self.candidates:
            if (len(self.candidates) > 1):
                p = Process(target=self.__multiproc_candidate_scoring__, args=(cand, cand_queue, avg_score))
                p.start()
                jobs.append(p)
            else:
                res.append(cand)

        for job in jobs:
            res.append(cand_queue.get())

        # Not necessary?
        for job in jobs:
            job.join()

        self.candidates = res

        self.__scale_scores__()

        self.candidates.sort(key=lambda x: x.score, reverse=True)
       
        if (self.candidates[0].score > 0):
            self.candidates = [c for c in self.candidates if c.score > self.candidates[0].score/2]
        #self.candidates = [self.candidates[0]]
        #self.__scale_scores__()

       
        if (len(self.candidates) > 1):
            self.winner_ratio = self.candidates[0].score / self.candidates[1].score
        else:
#            print("velger", self.candidates[0].name, "fordi den er overlegen")
            self.candidates[0].score = 1

        entity_queue.put(self)
'''

    def __scale_scores__(self):
        sum = 0
        for c in self.candidates:
            sum += c.score

        if sum > 0:
            for c in self.candidates:
                c.score /= sum
        else:
            for c in self.candidates:
                c.score = 1/len(self.candidates)

    def __longest_common_substring__(self, s1, s2):
        m = [[0] * (1 + len(s2)) for i in range(1 + len(s1))]
        longest = 0
        for x in range(1, 1 + len(s1)):
            for y in range(1, 1 + len(s2)):
                if s1[x - 1] == s2[y - 1]:
                    m[x][y] = m[x - 1][y - 1] + 1
                    if m[x][y] > longest:
                        longest = m[x][y]

        if (longest > 4): # Should be 4/5?
            return longest/min(len(s1), len(s2))/max(len(s1), len(s2))
            #return (pow(1.15, longest))/max(len(s1), len(s2))/min(len(s1), len(s2))
        return 0.0


    def __str__(self):
        res = self.name + " ("
        try:
            res += self.neighbors[0].name
            for n in self.neighbors[1:]:
                res += ", " + n.name
        except: # No neighbors
            pass

        res += ")\n"#  Candidates: " + str(len(self.candidates)) 
        
        #if len(self.candidates) > 1:
        #res += ", winner: " + str(self.winner_ratio) + "\n"
            
        for c in self.candidates:
            res += c.__str__()
        res += "\n"

        return res
    
