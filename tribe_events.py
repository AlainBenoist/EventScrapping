#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import pprint 
import requests
import json
import html
import re

#
#   Tribe_events ---
#   A class that stores and gives access to all events, venues and organizers stored on a wordpress site with 'The Events Calendar' plugin
#   This class requires that the JSON/REST/API be enabed on the wordpress site
#
class tribe_events :
    verbose = False
    event_count = 0
    venue_count = 0
    organizer_count = 0
    sitename = ''
    venues = []
    events = []
    organizers = []

    def post_organizer(self, slug, organizer_name) :
        organizer = {
            "organizer" : html.escape(organizer_name),
            "description" : "Test",
            "phone": "06.01.01.10.87",
            "website": "http://org.com",
            "email": "contact@org.com",
            }
        url_link = self.sitename+'/wp-json/tribe/events/v1/organizers/by-slug/'+slug
        headers = {'content-type': 'application/json'}

        r = requests.post(url_link, data=json.dumps(organizer), headers=headers)
        if r.ok :
            data = json.loads(r.content)
            if( self.verbose ) :
                print(json.dumps(data, sort_keys=True, indent=4))
        else :
            print("Error in post_organizer :", r.status_code)
        
    # Print an organizer
    def print_organizer(self, organizer) :
        organizer_id = 0
        name = url = email = phone = slug = ''
    
        # Retrieve the detail of organizers
        organizer_id = organizer['id']
        
        # The title may contain some html escaping sequences (ex: &lt for <)
        if ( 'organizer' in organizer ) :
            name = html.unescape(organizer['organizer']).strip()

        if ( 'url' in organizer ) :
            url = html.unescape(organizer['url']).strip()

        if ( 'email' in organizer ) :
            email = html.unescape(organizer['email']).strip()
 
        if ( 'phone' in organizer ) :
            phone = html.unescape(organizer['phone']).strip()
            
        if ( 'slug' in organizer ) :
            slug = html.unescape(organizer['slug']).strip()
                                    
        print (name + '(' + str(organizer_id)+')')
        print (email + " " + phone)

    # Print all organizers
    def print_all_organizers(self) :
        for organizer in self.organizers :
            self.print_organizer(organizer)
            print('---- ooo ----')
    
    # Get a particular organizer by id
    def get_organizer_by_id(self, id) :
        for organizer in self.organizers :
            if ( organizer['id'] == id ) :
                return organizer
        return None

    # Get a particular organizer by name
    # Returns a list of organizers
    def get_organizers_by_name(self, name) :
        organizers = []
        
        for organizer in self.organizers :
            if ( 'organizer' in organizer and html.unescape(organizer['organizer']) == name ) :
                organizers.append(organizer)
        return organizers

    # Initial loading of organizers
    def init_organizers(self) :
        url_link = self.sitename+'/wp-json/tribe/events/v1/organizers/?per_page=50'

        self.organizers_count = 0
        while url_link != '' :
            r = requests.get(url_link,)

            if r.ok:
                data = json.loads(r.content)
            else :
                break

            if( self.verbose ) :
                print(json.dumps(data, sort_keys=True, indent=4))

            # Go through the list of organizers - an organizer is a dictionnary
            for organizer in data['organizers']:
                self.organizers.append(organizer)
                                                       
                if ( self.verbose ) :
                    self.print_organizer(organizer)

                self.organizer_count += 1
            
            if ( 'next_rest_url' in data ) :
                url_link=data["next_rest_url"]
            else :
                url_link = ''

    # Print a venue
    def print_venue(self, venue) :
        venue_id = description = address = city = zip = coutry = url = slug = ''
    
        # Retrieve the detail of venues
        venue_id = venue['id']
        
        # The title may contain some html escaping sequences (ex: &lt for <)
        venue_name = html.unescape(venue['venue']).strip()
    
        if ( 'description' in venue ) :
            description = html.unescape(venue['description'])
            
        if ( 'address' in venue ) :
            address = html.unescape(venue['address']).strip()

        if ( 'city' in venue ) :
            city = html.unescape(venue['city']).strip()

        if ( 'zip' in venue ) :
            zip = html.unescape(venue['zip']).strip()

        if ( 'country' in venue ) :
            country = html.unescape(venue['country']).strip()

        if ( 'url' in venue ) :
            url = html.unescape(venue['url']).strip()

        if ( 'slug' in venue ) :
            slug = html.unescape(venue['slug']).strip()
                                    
        print (venue_name)
        print (address)
        print (zip + " " + city)

    # Print all venues
    def print_all_venues(self) :
        for venue in self.venues :
            self.print_venue(venue)
            print('---- ooo ----')
    
    # Get a particular venue by id
    def get_venue_by_id(self, id) :
        for venue in self.venues :
            if ( venue['id'] == id ) :
                return venue
        return None

    # Get a particular venue by name
    # Returns a list of venues
    def get_venues_by_name(self, name) :
        venues = []
        
        for venue in self.venues :
            if ( html.unescape(venue['venue']) == name ) :
                venues.append(venue)
        return venues

    # Initial loading of venues
    def init_venues(self) :
        url_link = self.sitename+'/wp-json/tribe/events/v1/venues/?per_page=50'

        self.venue_count = 0
        while url_link != '' :
            r = requests.get(url_link,)

            if r.ok:
                data = json.loads(r.content)
            else :
                break

            if( self.verbose ) :
                print(json.dumps(data, sort_keys=True, indent=4))

            # Go through the list of venues - a venue is a dictionnary
            for venue in data['venues']:
                self.venues.append(venue)
                                                       
                if ( self.verbose ) :
                    self.print_venue(venue)

                self.venue_count += 1
            
            if ( 'next_rest_url' in data ) :
                url_link=data["next_rest_url"]
            else :
                url_link = ''

    # Print one event 
    def print_event(self, event) :                    
        event_name = event_description = event_url = event_cost = event_image = start_date = end_date = ''
        venue_name = venue_description = address = city = zip = country = venue_url = venue_slud = ''
        event_id = venue_id = 0

        # Retrieve event information
        event_id = event['id']
        event_name = html.unescape(event['title']).strip()
        
        if ('description' in event ) :
            event_description = html.unescape(event['description'])
        if ('url' in event ) :
            event_url = event['url']
        if ( 'start_date' in event ) :
            start_date = event['start_date'][:10]
        if ( 'end_date' in event ) :    
            end_date = event['end_date'][:10]
        if ( 'cost' in event ) :
            event_cost = event['cost']
        if ( 'image' in event ) :
            if ( event['image'] and 'url' in event['image'] ) :
                event_image = event['image']['url']

        # Retrieve venue information
        if ( 'venue' in event ) :
            venue = event['venue']

            venue_id = venue['id']
            venue_name = html.unescape(venue['venue']).strip()
    
            if ( 'description' in venue ) :
                venue_description = html.unescape(venue['description'])
            
            if ( 'address' in venue ) :
                address = html.unescape(venue['address']).strip()

            if ( 'city' in venue ) :
                city = html.unescape(venue['city']).strip()

            if ( 'zip' in venue ) :
                zip = html.unescape(venue['zip']).strip()

            if ( 'country' in venue ) :
                country = html.unescape(venue['country']).strip()

            if ( 'url' in venue ) :
                venue_url = html.unescape(venue['url']).strip()

            if ( 'slug' in venue ) :
                venue_slug = html.unescape(venue['slug']).strip()


        print ("Title :  "+event_name+ "(%d)" %event_id)
        print ("Descr :  "+event_description)
        print ("Start :  "+start_date)
        print ("End   :  "+end_date)
        print ("URL   :  "+event_url)
        print ("Venue :  "+ "("+str(venue_id) +") "+venue_name+" / "+city)
        print ("Cost  :  "+event_cost)
        print ("Image :  "+event_image)
    
    # Print all events 
    def print_all_events(self) :
        for event in self.events :
            self.print_event(event)
            print ("---- ooo ----")

    # Get a particular event by id
    def get_event_by_id(self, id) :
        for event in self.events :
            if ( event['id'] == id ) :
                return event
        return None

    # Get a particular event by name
    def get_events_by_name(self, name) :
        events = []

        # Replace all non alphanumeric characters par space 
        name2 = re.sub('[^0-9a-zA-Z]+',' ', name)
        for event in self.events :
            title=html.unescape(event['title'])
            title2 = re.sub('[^0-9a-zA-Z]+',' ', title)

            if ( title2.strip().upper() == name2.strip().upper() ) :
                events.append(event)
        return events
    
    # Initial loading of events            
    def init_events(self) :
        url_link = self.sitename+'/wp-json/tribe/events/v1/events/?per_page=5'

        self.event_count=0
        while url_link != '' :
            r = requests.get(url_link,)

            if r.ok:
                data = json.loads(r.content)
            else :
                break

            if ( self.verbose ) :
                print(json.dumps(data, sort_keys=True, indent=4))

            for event in data["events"]:
                self.events.append(event)

                self.event_count += 1
                if ( 'next_rest_url' in data ) :
                    url_link=data["next_rest_url"]
                else :
                    url_link = ''


    def __init__(self, SiteName='https://dibutade.fr'):
        self.sitename=SiteName
        self.init_organizers()
        self.init_venues()
        self.init_events()
        if ( self.verbose ) :
            self.print_all_organizers()
            self.print_all_venues()
            self.print_all_events()

        if ( self.verbose ) :
            print("Organ. count = "+str(self.organizer_count))
            print("Events count = "+str(self.event_count))
            print("Venues count = "+str(self.venue_count))
