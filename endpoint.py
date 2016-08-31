import tornado.web
from selenium import webdriver
import sys
import psycopg2
from selenium.common.exceptions import NoSuchElementException


class LevelHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        connection = self.settings['connection']
        self.cursor = connection.cursor()

    def get(self, word):
        driver = webdriver.PhantomJS(executable_path=r'bin/phantomjs')
        driver.get(url="http://dictionary.cambridge.org/dictionary/english/%s" % word)
        is_word_cached = self.check_cache(word)
        self.set_header("Access-Control-Allow-Origin", "*")
        if is_word_cached:
            response = {'level': is_word_cached[0][0], 'word': word}
        elif self.check_word_404(driver):
            response = {'level': "This word was not found", 'word': word}
        else:
            try:
                level = driver.find_element_by_xpath(xpath="//span[@class='def-info']/span[contains(@title,'A1-C2')]")
                level = level.text
            except NoSuchElementException:
                level = "The word level is not known"
            self.write_cache(word, level)
            response = {'level': level, 'word': word}

        self.write(response)

    def check_cache(self, word):
        self.cursor.execute("SELECT level FROM eng_level WHERE word = %s", (word,))
        records = self.cursor.fetchall()
        return records

    def write_cache(self, word, level):
        self.cursor.execute("INSERT INTO eng_level (word, level) values (%s, %s)", (word, level,))
        self.cursor.execute("COMMIT")

    def check_word_404(self, driver):
        try:
            return driver.find_element_by_xpath(xpath="//h1[contains(text(),'404. Page not found.')]")
        except NoSuchElementException:
            return False


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
