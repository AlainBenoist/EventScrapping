#!/usr/bin/env python
# coding: utf-8
# Events page retrieval from spectable.com
# TO DO:

# Revue du filtrage et extraction des catégories et thèmes 
# Verifier titre quand export - présence d'escape characters html ?
# verifier comportement de get_text() pour les descriptions d'événemens (' ' ou '\n')
# title() pour le nom des événements
# Ajouter les informations complémentaires (horaires et prix) à la description de l'événement
# Organisateur et numero de téléphone
# Ajouter département à partir du code postal

import codecs
import requests
from bs4 import BeautifulSoup
import csv
import html
import re
from datetime import date
import tribe_events


debug = 0

# We are looking for the following attributes in the page - Beware of character coding - ensure that the shell running python uses the same character encoding as the text editor of this script !!
EventAttr = [   'EventName', 'EventType', 'EventThemes', 'EventDates',
                'StartDate', 'EndDate', 'StartTime', 'EndTime',
                'EventCost', 'EventCurrency',
                'VenueName','VenueAddress','VenueZipCode','VenueCity', 'VenueCountry', 'ShowGoogleMap','ShowGoogleMapLink',
                'EventDescription',
                'ImageURL','ImageSrc',
                'Horaires', 'EventPricing', 'AddInfo', 'EventWebSite']
EventFileName = 'SpectableEvents.csv'

VenueAttr = [   'VenueName','VenueAddress','VenueZipCode','VenueCity', 'VenueCountry', 'ShowGoogleMap','ShowGoogleMapLink' ]
VenueFileName = 'SpectableVenues.csv'

MainURL='https://www.spectable.com/ile-de-france/agenda-culturel/exposition/n_61-l_35.php'

#   Cost parsing
#   Returns the highest number in string
#   Returns '0' ig contains 'Grat' or 'Lib'

def parse_cost(costing) :
    cost = 0
    
    if (costing is None or costing == '') :
        return ''

    list=re.findall('[0-9]+\s*(?=[€eE])|\s*[0-9]?[0-9]\s*$', costing)
    if ( len(list) == 0 ) :
        if ( re.match('.*[Gg][Rr][Aa][Tt].*|.*[Ll][Ii][Bb].*', costing) ):
            return '0' #Gratuit
        else :
            return ''  #Cost unknown
    
    for item in list :
        value=int(item)
        if ( value > cost ) :
            cost = value
    return str(cost)

#   Time parsing
#   Can recognize expressions like :
#       10h à 19h30
#       10-19H
#       10:30 20:30
#   But not
#       10-19
def parse_timing(timing) :
    start_time = '23:59'
    end_time = '00:00'
    
    list=re.findall('[0-2]?[0-9]\s*[Hh:]\s*[0-5][0-9]|[0-2]?[0-9]\s*[Hh]|[0-2]?[0-9]\s*(?:[àA-])', timing)
    if ( len(list) == 0 ) :
        return ['', '']
    
    for item in list :
        # normalize the time
        hours = minutes = 0
        found_hours = False
        
        fields = re.split('\D', item)
        for field in fields :
            if ( field != '' ) :
                if found_hours == False :
                    hours = int(field)
                    found_hours = True
                else :
                    minutes = int(field)
                    
        time = '{:02d}:{:02d}'.format(hours, minutes)

        if (time < start_time ):
            start_time = time
        if ( time > end_time and time < '23:59' ) :
            end_time = time
    
    return [ start_time, end_time ]

#   Dates parsing
#   the dates formats recognized are of the following types
#       Le 23 juin 2018
#       Du 10 avril 2018 au 14 avril 2018
#   This fonction takes as parameters
#       a string containing the dates
#   This function returns
#       a list of two dates or en empty list
def parse_dates(dates) :
    month_table = { 'JANVIER' : 1, 'JAN' : 1,
                    'FÉVRIER' : 2,'FEVRIER' : 2,'FEV' : 2,
                    'MARS' : 3, 'MAR' : 3,
                    'AVRIL' : 4, 'AVR' : 4,
                    'MAI' : 5,
                    'JUIN': 6, 'JUN' : 6,
                    'JUILLET' : 7, 'JUL' : 7,
                    'AOUT' : 8, 'AOÛT' : 8, 'AOU' : 8,
                    'SEPTEMBRE' : 9, 'SEP' : 9, 'SEPT' : 9,
                    'OCTOBRE' : 10, 'OCT' : 10, 
                    'NOVEMBRE' : 11, 'NOV' : 11, 
                    'DÉCEMBRE' : 12, 'DECEMBRE' : 12 , 'DEC' : 12 }
    day = month = year= 0
    date = [[0,0,0],[0,0,0]]
    start_date = end_date = ''
    index = 0
    
    for string in dates.split() :
        string = string.upper()
        if ( string in [ 'DE', 'A', 'LE', 'DU' ] ) :
             continue
        if ( string in [ 'LUNDI', 'MARDI', 'MERCREDI', 'JEUDI', 'VENDREDI', 'SAMEDI', 'DIMANCHE'] ) :
             continue
        if ( string in month_table ) :
             month = month_table[string.upper()]
        if ( string.isdecimal() ) :
            number = int(string)
            if ( number > 0 and number < 32 ) :
                day = number
                continue
            if ( number > 2010 and number < 2030 ) :
                year = number
        if ( day > 0 and month > 0 and year > 0 ) :
             date[index] = [ year, month, day ]
             index = index+1
             day = month = year = 0
        if ( index > 1 ) :
            break
             
    if ( index >= 1 ) :
        end_date = start_date = '%04d' %date[0][0] + '/'+ '%02d' %date[0][1] + '/' + '%02d' %date[0][2]
    if ( index > 1 ) :
        end_date = '%04d' %date[1][0] + '/' + '%02d' %date[1][1] + '/' + '%02d' %date[1][2]
    # Verify that start_date precedes end_date
    
    if ( debug ):
        print(dates+"="+start_date+":"+end_date)
    
    return [ start_date, end_date ]

#
#   spectable_events
#   This class regroups all functions that allow to parse event from spectable.com
class spectable_events :
    event_types = [ 'Expositions' ]    # type of events ex: Exposition
    event_themes = ['Peinture', 'Sculpture', 'Modelage', 'Autres', 'Estampe', 'Salons']    # Focus of events ex: Peinture, Sculpture
    main_url = ''
    current_url = ''
    next_url = ''
    soup = None
    event = None

    # Retrieve the content of the event described in a given URL
    def get_event(self, url) :
        infomap = {
            'Horaires'  : 'Horaires',
            'Tarifs'    : 'EventPricing',
            'A savoir'  : 'AddInfo',
            'Sur le net': 'EventWebSite',
            }           # Traduction table for additional/optional informations 
        data = {}
        title = event_type = event_theme = ''
        today=date.today()
        
        if ( debug ):
            print(url)

        # Retrieve the page for the URL
        page = requests.get(url)
        if page.status_code > 200 :
            print(url+ ": Erreur "+page.status_code)
            return data

        # Requests does not always recognize the right encoding so we force it
        page.encoding='utf-8'

        # Parse the page
        soup = BeautifulSoup(page.text, 'html.parser') 
        if ( debug ) :
            print(soup.prettify())
            
        # Retrieve the title of the page
        title=soup.h1
        if ( title is not None ) :
            title = html.unescape(title.string)
        else :
            return []
        
        if ( debug ) :
            print(title)
        
        # Retrieve topic of expositions
        for topic in soup.find_all('div', class_='sous_poucet') :
            category = topic.get_text(' ')
            if ( debug ) :
                print (category)

        # Determine if this is an interesting category for us
        for item in category.split() :
            if ( item in self.event_types ) :
                event_type = item
                
            if ( item in self.event_themes ) :
                event_theme += item + " "
                
        # if the event does not belong to the required nature and theme, we stop here
        #if ( len(event_type) == 0 or len(event_theme) == 0 ):
        #   return []
        
        try :
            dates = venue = address = city = image = image_name = image_url = description = start_time = end_time = cost = ''

            # Retrieve the dates of the event
            header=soup.h1.find_next('header')
            dates_src=header.find_next('time')
            dates=dates_src.get_text().strip()
            if (debug ) :
                print(dates)

            # extract the start_date and end_date
            date_range = parse_dates(dates)
            start_date = date_range[0]
            end_date = date_range[1]
            if ( debug ) :
                print(dates+">>"+start_date+":"+end_date)    

            # retrieve the venue name
            venue_src=dates_src.find_next('a')
            venue=venue_src.get_text()
            if ( debug ) :
                print(venue)
            # and the address
            address_src=dates_src.find_next('span')
            if address_src is not None :
                address=address_src.get_text().strip()
            if ( debug ) :
                print(address)
            # With the City name and Zip Code
            city_src=venue_src.find_next('a')
            if city_src is not None :
                city = city_src.get_text()
                zip_pos = city.find("(")
                zip_code = city[zip_pos+1:zip_pos+6]
                city = city[0:zip_pos]
            if ( debug ) :
                print (city + "[" + zip_code+"]")
                
            # Locate the image associated with the event 
            figure=header.find_next('figure')
            image_src=figure.find_next('img')
            if image_src is not None :
                image=image_src.get('src')
                if ( image.startswith('http') is False ) :
                    image = ''
                    image_url = ''
                else :
                    # determine file extension
                    pos_extension = image.rfind('.')
                    file_extension = image[pos_extension:]
                    
                    # Replace all nom alphanumeric characters in the title by '_' to derive a new image name
                    image_name = re.sub('[^0-9a-zA-Zàçéèêëîöüù]+','_', title)+file_extension
                    # And construct the full name of the image after it is loaded as a media on dibutade.fr
                    folder='{:d}/{:02d}/'.format(today.year, today.month)
                    image_url = 'https://dibutade.fr/wp-content/uploads/'+folder+image_name
                
            # And the description of the event
            description_src=figure.find_next('p')
            if description_src is not None :
                description=description_src.get_text(' ')

            # Then find the additional informations on the page 
            for info in soup.find_all('h3') :
                if ( debug ) :
                    print(info.text)
                if ( info.text in infomap ) :
                    info_data=info.find_next('p')
                    if info_data is not None :
                        if ( debug ) :
                            print(">>"+info_data.get_text())
                    
                        data[infomap[info.text]]=info_data.get_text(' ')
                        if info.text == 'Horaires' :
                            times = parse_timing(info_data.get_text(' '))
                            start_time = times[0]
                            end_time = times[1]
                        if info.text == 'Tarifs' :
                            cost = parse_cost(info_data.get_text(' '))
        except :
            print("-- Erreur parsing data ---")
            print(soup.prettify())
            return []

        data['EventName']=title
        data['EventType']=event_type
        data['EventThemes']=event_theme
        data['EventDates']=dates
        data['StartDate']=start_date
        data['EndDate']=end_date
        data['VenueName']=venue
        data['VenueAddress']=address
        data['VenueZipCode']=zip_code
        data['VenueCity']=city
        data['VenueCountry']='France'
        data['EventDescription']=description
        data['ImageSrc']=image
        data['ImageName']=image_name
        data['ImageURL']=image_url
        data['StartTime']= start_time
        data['EndTime']=end_time
        data['EventCost']=cost
        data['EventCurrency']='€'
        data['ShowGoogleMap']='TRUE'
        data['ShowGoogleMapLink']='TRUE'

        del page
                
        return data

    # Method to display the next 'useful' event in the collection
    def next_event(self) :
        if ( self.event is None ) : # First time initialization
            # Initialize the page
            self.next_url = self.main_url
        else :
            self.event = self.event.find_next('article', class_='a')
            
        # While there are pages to come
        while (self.next_url != '') :
            # Search for links to events in the current page
            while ( self.event is not None ) :
                header = self.event.find_next('header')
                if ( debug ):
                    print (header.prettify())
                url = header.a.get('href')
                if ( debug ) :
                    print(url)
                if ( url.startswith('https://www.spectable.com') ) :
                    data=self.get_event(url)
                    if ( len(data) > 0 ):
                        if ( debug ) :
                            for item in data :
                                if ( item == 'Description' ) :
                                    continue
                                print (item.ljust(15) +": " + data[item])
                                print ('========================= ooo =========================')
                        return data
                self.event = self.event.find_next('article', class_='a')
                
            # If an interesting event has not been found - move to the next page        
            self.current_url = self.next_url 
            page = requests.get(self.current_url)
            if page.status_code > 200 :
                print(self.current_url+ ": Erreur "+page.status_code)
                return {}
            page.encoding='utf-8'

            self.soup = BeautifulSoup(page.text, 'html.parser')
            if ( debug ) :
                print(self.soup.prettify())
                Wait=input("Appuyez sur une touche")
                
            # find the next page URL
            next_page=self.soup.find('div', class_='n ')
            if (next_page is None ) :
                self.next_url = ''
                return None
            else :
                self.next_url=next_page.a.get('href')
                
            # Find the title of the page - serving as a reference to fetch the next article 
            self.event = self.soup.find('article', class_='a')
            if ( self.event is None ) :
                return None
        self.current_url=''
        return None

            
    def __init__(self, region='ile-de-france', event_type = 'exposition', filter = []) :
        
        region_code = {
                      'corse' : 'l_46' ,   
                      'nord-pas-de-calais' : 'l_40' , 
                      'picardie' : 'l_42' ,    
                      'haute-normandie' : 'l_34' ,   
                      'limousin' : 'l_37' ,   
                      'bretagne' : 'l_31' ,   
                      'champagne-ardenne' : 'l_149' ,   
                      'lorraine' : 'l_38' ,  
                      'alsace' : 'l_26' ,   
                      'franche-comte' : 'l_33' ,  
                      'ile-de-france' : 'l_35' ,  
                      'centre' : 'l_32' ,  
                      'auvergne' : 'l_28' ,  
                      'bourgogne' : 'l_30' ,  
                      'pays-de-la-loire' : 'l_41' , 
                      'basse-normandie' : 'l_29' , 
                      'aquitaine' : 'l_27' ,  
                      'midi-pyrenees' : 'l_39' , 
                      'provence-alpes-cote-d-azur' : 'l_44' ,   
                      'rhone-alpes' : 'l_45' ,   
                      'poitou-charentes' : 'l_43' ,  
                      'languedoc-roussillon' : 'l_36' , 
                      'dom-tom' : 'l_47' }

        event_code = {
                      'concert/musique' : 'n_62',
                      'spectacle/danse' : 'n_301',
                      'theatre' : 'n_63',
                      'exposition' : 'n_61',
                      'exposition/peinture' : 'n_305',
                      'exposition/photo' : 'n_306',
                      'exposition/sculpture-modelage' : 'n_307',
                      'exposition/estampe' : 'n_3041',
                      'salon-foire' : 'n_1987',
                      'spectacle/enfant' : 'n_300',
                      'spectacle/cinema-audiovisuel' : 'n_2427',
                      'spectacle/art-rue-piste' : 'n_302',
                      'spectacle/humour-cabaret' : 'n_303',
                      'scene-ouverte-jam-session' : 'n_3251',
                      'conferences-rencontres' : 'n_3257',
                      'animations-locales' : 'n_3004' }
        if event_type in event_code :
            event_slug = event_type+'/'+event_code[event_type]
        else :
            event_slug = 'n_2'      # All kind of events
            

        if ( region in region_code ):
            self.main_url = 'https://www.spectable.com/' + region + '/agenda-culturel/' + event_slug + '-' + region_code[region] +'.php'
        else :
            self.main_url = 'https://www.spectable.com/agenda-culturel/' + event_slug +'.php'
                
        print(self.main_url)

#
#   Save the venues in a CSV file 
def file_venues(venues, tribe_events) :
    
    with codecs.open(VenueFileName, 'w', 'utf-8') as csv_file :
        writer = csv.DictWriter(csv_file, VenueAttr, restval='', extrasaction='ignore', delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)

        writer.writeheader()

        # Write the venues
        for name in venues :
            # Find if venue already exist in 'dibutade.fr'
            existing = False
            matching_venues = tribe_events.get_venues_by_name(name)
            for venue in matching_venues :
                existing = True

            if ( existing is False ) :
                writer.writerow(venues[name])

        
            
if __name__ == '__main__':

    venues = {}

    # Initialize the class that accesses the events present on dibutade.fr
    t=tribe_events.tribe_events('https://dibutade.fr')
        
    # Initialize the spectable_events class
    s=spectable_events(region='ile-de-france',event_type='exposition')
    
    # Open the CSV file that will contain the events
    with codecs.open(EventFileName, 'w', "utf-8") as csv_file :
        writer = csv.DictWriter(csv_file, EventAttr, restval='', extrasaction='ignore', delimiter=',', quotechar='"', quoting=csv.QUOTE_NONNUMERIC)

        # Write header row in the csv file 
        writer.writeheader()
        
        # Retrieve the first event on Spectable
        data = s.next_event()
        while (data is not None ) :
            existing = False
            
            # Check if the event is already on dibutade.fr
            matching_events = t.get_events_by_name(data['EventName'])
            for event in matching_events :
                if ( debug ) :
                    print(">>"+html.unescape(event['title'])+' existing in dibutade.fr')
                existing = True
                
            if ( existing is False ) :
                # Show event
                for item in data :
                    print (item.ljust(15) +": " + data[item])
                print ('========================= ooo =========================')
                
                # If not existing, ask if we want to integrate this new event ...
                answer=input("Voulez-vous intégrer cet événement ? ")
                #answer='y'
                if ( answer == 'o' or answer == 'O' or answer == 'y' or answer == 'Y' or answer == '' ) :
                    # Save data in Events CSV file		
                    writer.writerow(data)

                    # Retrieve the picture of the event and save it the Images folder
                    if ( data['ImageSrc'] != '' ) :
                        img = requests.get(data['ImageSrc'], stream=True)
                        if (img.status_code <= 200 ) :				
                            with open("./Images/"+data['ImageName'], 'wb') as img_file :
                                    img_file.write(img.content)
                        del img
                        
                    # Save the Venue informations for later
                    venue = {}
                    for item in VenueAttr :
                        venue[item] = data[item]
                    venues[data['VenueName']]=venue
                    
            # Move to the next event 
            data = s.next_event()

        # Save the venues
        file_venues(venues, t)
     

    
    
