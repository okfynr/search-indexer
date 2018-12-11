import json
import re
import html2text
#import functools
import os


class Indexer:
    def __init__(self):
        self.analyser = HtmlAnalyser()
        self.tokenizer = StandartTokenizer()
        self.index = {}
        self.files = []

    def index_files(self, files, basePath, baseUrl="./"):
        fi = len(self.files)
        for file in files:
            # create file entry
            with open(file, 'r', encoding='utf8', errors='ignore', newline='\n') as myfile:
                contents = myfile.read().replace('\r\n', '').replace('\n', '')
                myfile.close()

            self.files.append(self.generate_file_info(file, contents, basePath, baseUrl))

            # analyse
            for index in self.analyser.analyse(contents, self.tokenizer):
                for word in index:
                    # word['t'] is token
                    # word['w'] is weight
                    if not word['t']:
                        continue

                    if not word['t'] in self.index:
                        self.index[word['t']] = []

                    if len(self.index[word['t']]) <= fi:
                        self.index[word['t']].append({'f': fi, 'w': word['w']})
                    else:
                        self.index[word['t']][fi]['w'] *= word['w']
            fi = fi + 1


    def generate_file_info(self, file, contents, basePath, baseUrl):
        # create file entry
        matches = re.search("<h1>(.*?)</h1>", contents)
        matches2 = re.search("<title>(.*?)</title>", contents)
        if matches:
            title = html2text.html2text(matches.group(0))[:-2]
        elif matches2:
            title = html2text.html2text(matches2.group(0))[:-2]
        else:
            title = "<i>No title</i>"
        return {"url": baseUrl + file[len(basePath):].replace(' ', '%20'),
                "title": title}

    def exportJs(self):
        text = '''
jssearch.index = {index};     
jssearch.files = {files};
jssearch.tokenizeString = {tokenizeString};
        '''
        return text.format(index=json.dumps(self.index),
                           files=json.dumps(self.files),
                           tokenizeString=self.tokenizer.tokenize_js())


class HtmlAnalyser:
    def __init__(self):
        self.headWeight = 20
        self.titleWeight = 4
        self.textWeight = 1.2

    def analyse(self, string, tokenizer):
        index = [
                    self.__find_text(string, "<h\d>(.*?)</h\d>", {"text": 2, "weight": 1}, tokenizer,
                                     lambda w, h: w * abs(self.headWeight - h) / 10),
                    self.__find_text(string, "<title>(.*?)</title>", {"text": 1},         tokenizer, self.titleWeight),
                    self.__find_text(string, "<p>(.*?R?)</p>", {"text": 1},               tokenizer, self.textWeight),
                    self.__find_text(string, "<(th|td|li|dd|dt)>(.*?)</(th|td|li|dd|dt)>", {"text": 2}, tokenizer, self.textWeight)]

        #wordCount = functools.reduce(lambda carry, item: carry + len(item), index, 0)
        #for i, words in index.items():
        #   for w, word in words.items():
        #       not that good formula
        #       index[i][w]['w'] = 1 + index[i][w]['w'] /wordCount

        return index

    def __find_text(self, string, pattern, selectors, tokenizer, weight):
        matches = re.findall(pattern, string)
        index = []
        if matches :
            i = 0
            for match in matches:
                if type(match) == tuple:
                    match = match[1]
                tokens = tokenizer.tokenize(html2text.html2text(match))

                for token in tokens:
                    if callable(weight):
                        result_weight = weight(token['w'], len(match[selectors['weight']]))
                        index.append({'t': token['t'], 'w': token['w'] * result_weight})
                    else:
                        index.append({'t': token['t'], 'w': token['w'] * weight})

                i = i + 1

        return index


class StandartTokenizer:
    def __init__(self):
        self.stopWords = ["a", "an", "and", "are", "as", "at", "be", "but", "by",
                          "for", "if", "in", "into", "is", "it",
                          "no", "not", "of", "on", "or", "such",
                          "that", "the", "their", "then", "there", "these",
                          "they", "this", "to", "was", "will", "with"]
        self.delimeters = ".,;:\\/[](){} \"'!?@#$%&*_-<>+="

    def tokenize(self, string):
        words = re.split('|'.join(map(re.escape, self.delimeters + '\n')), string, 0)

        words1 = []
        for item in words:
            words1.append(item.lower().replace("\n", ""))

        filter(lambda word: word in self.stopWords or word == '', words1)

        tokens = []
        for item in words1:
            tokens.append({'t': item, 'w': 1})

        return tokens

    def tokenize_js(self):
        text = '''
function(string) {{
        var stopWords = {stopWords};
return string.split(/[\s{delimeters}]+/).map(function(val) {{
    return val.toLowerCase();
}}).filter(function(val) {{
    for (w in stopWords) {{
        if (stopWords[w] == val) return false;
    }}
    return true;
}}).map(function(word) {{
    return {{t: word, w: 1}};
}});
}}
        '''
        return text.format(
            stopWords=json.dumps(self.stopWords),
            delimeters=re.escape(self.delimeters)
        )


def find_files(direct, ext="html"):
    files_list = []
    for root, dirs, files in os.walk(direct):
        for i in files:
            file = os.path.join(root, i)

            if file[len(file) - len(ext): len(file)] == ext:
                files_list.append(os.path.join(root, i))
    return files_list


if __name__ == "__main__":
    ind = Indexer()
    directory = "absolute path to files"
    files = find_files(directory)
    ind.index_files(files, directory)

    with open("jssearch.index.js", 'w') as myoutfile:
        myoutfile.write(ind.exportJs())
        myoutfile.close()



