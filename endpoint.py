import tornado.web
import sys
import psycopg2
from lxml import html
import requests


class LevelHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        connection = self.settings['connection']
        self.cursor = connection.cursor()

    def get(self, word):
        page = requests.get('http://dictionary.cambridge.org/dictionary/english/%s' % word)
        tree = html.fromstring(page.content)
        is_word_cached = self.check_cache(word)
        if is_word_cached:
            response = {'level': is_word_cached[0][0], 'word': word}
        elif self.check_word_404(tree):
            response = {'level': "This word was not found", 'word': word}
        else:
            try:
                level = tree.xpath("//span[@class='def-info']/span[contains(@title,'A1-C2')]/text()")
                level = level[0]
            except IndexError:
                level = "The word level is not known"
            self.write_cache(word, level)
            response = {'level': level, 'word': word}
        self.set_header("Access-Control-Allow-Origin", "*")
        self.write(response)

    def check_cache(self, word):
        self.cursor.execute("SELECT level FROM eng_level WHERE word = %s", (word,))
        records = self.cursor.fetchall()
        return records

    def write_cache(self, word, level):
        self.cursor.execute("INSERT INTO eng_level (word, level) values (%s, %s)", (word, level,))
        self.cursor.execute("COMMIT")

    def check_word_404(self, tree):
        return len(tree.xpath("//h1[contains(text(),'404. Page not found.')]/text()")) > 0



class AngularHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("ui.html")


conn_string = "creds"
conn = psycopg2.connect(conn_string)
application = tornado.web.Application([
    (r"/([A-Za-z]+)", LevelHandler),
    ("/", AngularHandler)
], connection=conn)

if __name__ == "__main__":
    application.listen(str(sys.argv[1]))
    tornado.ioloop.IOLoop.instance().start()
