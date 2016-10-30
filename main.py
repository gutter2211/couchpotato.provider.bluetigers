# coding: utf8
from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.media._base.providers.torrent.base import TorrentProvider
from couchpotato.core.media.movie.providers.base import MovieProvider
from couchpotato.core.media._base.searcher.main import Searcher
import traceback
import json
import urllib2

log = CPLog(__name__)

class bluetigers(TorrentProvider, MovieProvider):

    baseurl = 'https://www.bluetigers.ca/'
    urls = {
        'test' : baseurl,
        'login' : baseurl + 'account-login.php',
        'login_check' : baseurl,
        'index' : baseurl + 'index.php',
        'search' : baseurl + 'torrents-search.php?search=%s',
        'detail' : baseurl + 'torrents-details.php?id=%s',
        'download' : baseurl + 'download.php?id=%s&name=%s.torrent'
    }

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _searchOnTitle(self, title, movie, quality, results):

        searcher = Searcher()
        index = self.getJsonData(self.urls['index'])

        if isinstance(title, str):
            title = title.decode('utf8')

        # movieYear = année du film référencée par CP
        movieYear = str(movie['info']['year'])
        frTitle = title
        # frTitle = titre version française récupéré sur TMDB
        frTitle = self.getFrenchTitle(title, movieYear)
        if frTitle is None:
            frTitle = title

        log.debug('#### CP is using this movie title : ' + title)
        log.debug('#### Searching BlueTigers for the FR title : ' + frTitle)

        if (self.conf('ignoreyear')):
            searchRequest = frTitle.encode('utf8')
        else:
            searchRequest = frTitle.encode('utf8') + " " + movieYear
        searchUrl = self.urls['search'] % urllib2.quote(searchRequest)
        data = self.urlopen(searchUrl)
        if data:
            try:
                html = BeautifulSoup(data)
                lin=1
                erlin=0
                resultdiv=[]
                while erlin==0:
                    try:
                        classlin='ttable_col'+str(lin)
                        resultlin=html.findAll(attrs = {'class' : [classlin]})
                        if resultlin:
                            for ele in resultlin:
                                resultdiv.append(ele)
                            lin+=1
                        else:
                            erlin=1
                    except:
                        erlin=1
                for result in resultdiv:
                    try:
                        new = {}
                        testname=0
                        resultb=result.find_all('b')
                        alltext=result.find_all(text=True)
                        for resulta in resultb:
                            name_real=str(resulta).replace("<b>","").replace("</b>","")
                            name=str(resulta).replace("<b>","").replace("</b>","").replace("."," ")
                            testname=searcher.correctName(name,frTitle)
                            if testname:
                               break
                        if not testname:
                           continue

                        idx = result.find_all('a')[1]['href'].replace('torrents-details.php?id=','').replace('&hit=1','')
                        detail_url = self.urls['detail'] % (idx)
                        url_download = self.urls['download'] % (idx,name_real)
                        size = None
                        for index,text in enumerate(alltext):
                            if 'Taille' in text:
                                size=alltext[index+1].replace('MB','').replace('GB','').replace(':','')
                                if 'GB' in alltext[index+1]:
                                    size = float(size) * 1024
                                break
                        age = '1'
                        def extra_check(item):
                            return True

                        new['id'] = idx
                        new['name'] = name.strip()
                        new['url'] = url_download
                        new['detail_url'] = detail_url
                        new['size'] = size
                        #new['age'] = self.ageToDays(str(age))
                        #new['seeders'] = tryInt(seeder)
                        #new['leechers'] = tryInt(leecher)
                        new['extra_check'] = extra_check
                        new['download'] = self.loginDownload
                        results.append(new)

                    except:
                        log.error('Failed parsing BlueTigers: %s', traceback.format_exc())

            except AttributeError:
                log.debug('No search results found.')
        else:
            log.debug('No search results found.')


    def getLoginParams(self):
        log.debug('Getting login params for BlueTigers')
        return {
             'username': self.conf('username'),
             'password': self.conf('password'),
        }

    def loginSuccess(self, output):
        log.debug('Checking login success for BlueTigers: %s' % ('True' if not output else 'False'))
        if not output.lower():
             return True
        else:
             return False

    loginCheckSuccess = loginSuccess

    def getFrenchTitle(self, title, year):
        """
        This function uses TMDB API to get the French movie title of the given title.
        """

        url = "https://api.themoviedb.org/3/search/movie?api_key=0f3094295d96461eb7a672626c54574d&language=fr&query=%s" % title
        log.debug('#### Looking on TMDB for French title of : ' + title)
        #data = self.getJsonData(url, decode_from = 'utf8')
        data = self.getJsonData(url)
        try:
            if data['results'] != None:
                for res in data['results']:
                    yearI = res['release_date']
                    if year in yearI:
                        break
                #frTitle = res['title'].lower().replace(':','').replace('  ',' ').replace('-','')
                frTitle = res['title'].lower().replace(':','').replace('  ',' ')
                if frTitle == title:
                    log.debug('#### TMDB report identical FR and original title')
                    return None
                else:
                    log.debug(u'#### TMDB API found a french title : ' + frTitle)
                    return frTitle
            else:
                log.debug('#### TMDB could not find a movie corresponding to : ' + title)
                return None
        except:
            log.error('#### Failed to parse TMDB API: %s' % (traceback.format_exc()))
