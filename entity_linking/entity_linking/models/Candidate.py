class Candidate:

    def __init__(self, name, subjects, weight, id):
        self.name = name    # string
        self.subjects = subjects    #list
        self.score = weight  # float       
        self.wiki_id = id   # string

    def __str__(self):
        res = "  " + self.name + " (" + self.wiki_id + ")\t(len: " + str(len(self.subjects))+ ", score: " + str(self.score) + ")\n"
        return res