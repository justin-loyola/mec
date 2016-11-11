#!/usr/bin/env python

"""
elasticrepublic.py -- Elastic Republic server-side Python App Engine API;
    uses Google Cloud Endpoints



"""

__author__ = 'mike.parziale@gmail.com (Michael Parziale)'


#from datetime import datetime, date, timedelta
import datetime
import json
import os
import time

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import urlfetch
from google.appengine.ext import ndb

from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import TeeShirtSize
from models import Relation
from models import RelationForm
from models import RelationForms
from models import BalanceHistory
from models import BalanceHistoryForm
from models import BalanceHistoryForms
from models import UserIDForm

from settings import WEB_CLIENT_ID
from settings import ANDROID_CLIENT_ID
from settings import IOS_CLIENT_ID
from settings import ANDROID_AUDIENCE

from utils import getUserId

EMAIL_SCOPE = endpoints.EMAIL_SCOPE
API_EXPLORER_CLIENT_ID = endpoints.API_EXPLORER_CLIENT_ID

ONE_BALLOT = float(1000000) #one millioon milionths of a Ballot
MONEY_TAX_RATE = 0.0006849315068493151  #float(1 / 1460) #Daily money tax rate: 1 divided by 1460 days in a term
BASIC_INCOME = 684.9315068493151  #float(ONE_BALLOT * TAX_RATE) #Daily Universal Basic Income 

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@endpoints.api( name='elasticrepublic',
                version='v1',
                audiences=[ANDROID_AUDIENCE],
                allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID, ANDROID_CLIENT_ID, IOS_CLIENT_ID],
                scopes=[EMAIL_SCOPE])
class ElasticRepublicApi(remote.Service):
    """Elastic Republic API v0.1"""


# - - - Relation objects - - - - - - - - - - - - - - - - -


    def _copyRelationToForm(self, rel):
        """Copy relevant fields from Conference to ConferenceForm."""
        rf = RelationForm()
        for field in rf.all_fields():
            if hasattr(rel, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('Date'):
                    setattr(rf, field.name, str(getattr(rel, field.name)))
                else:
                    setattr(rf, field.name, getattr(rel, field.name))
            elif field.name == "websafeKey":
                setattr(rf, field.name, rel.key.urlsafe())
            rf.check_initialized()
        return rf

    def _createRelationObject(self, request):
        """Create or update Relation object, returning RelationForm/request."""
        # preload necessary data items
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        
        if not request.name:
            raise endpoints.BadRequestException("Relation 'name' field required")

        # copy RelationForm/ProtoRPC Message into dict
        data = {field.name: getattr(request, field.name) for field in request.all_fields()}
        del data['websafeKey']
        del data['constitDisplayName']
        del data['repDisplayName']

        data ['constitUserId'] = cons_user_id = getUserId(user)
        
        # Set startDate to tadoy
        data['startDate'] = datetime.datetime.today()
            
        if data['oneTimeTransaction']:
            data['endDate'] = datetime.datetime.today()
        del data['oneTimeTransaction']

        
        # allocate new Relation ID 
        r_id = Relation.allocate_ids(size=1)[0]
        # make Relation key from ID
        r_key = ndb.Key(Relation, r_id)
        data['key'] = r_key

        data['version'] = 1

        # create Relation & return (modified) RelationForm
        rel = Relation(**data)
        rel.put() #save in Datastore
          
        return rel

    def _doRelation(self, request, change_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        rel = self._createRelationObject(request)
 
        csid = rel.constitUserId

        # get Profile entity from user ID
        cons_prof = ndb.Key(Profile, csid).get()
              
        r_key = rel.key
        #add this relation entity's key to the profile's active relations keys list
        cons_prof.activeRelationsKeys.append(r_key)

        cons_prof.put() #save in Datastore
        

        #add this relation entity's key to the repersentitves's profile's active relations keys list
        ruid = rel.repUserId
        
        repr_key = ndb.Key(Profile, ruid)
        repr_prof = repr_key.get()

        #If the representitve user is not already a reqistered ERBM user
        # create new Profile if not there
        if not repr_prof:
            
            bh_key = self._generateInitialBalanceHistory(repr_key)

            repr_prof = Profile(
                key = repr_key,
                userId = request.repUserId,
                displayName = request.repUserId,
                mainEmail= request.repUserId,
                teeShirtSize = str(TeeShirtSize.NOT_SPECIFIED),
                MostRecentBalanceHistoryKey = bh_key,
            )
        
        #add this relation entity's key to the rep profile's active relations keys list
        repr_prof.activeRelationsKeys.append(r_key)
        
        #save rep profile to Datastore
        repr_prof.put()

        #Make the constituents BalanceHistory Current
        cons_today_bh = self._MakeBalanceHistCurrent(cons_prof)

        #Make the representives BalanceHistory Current
        repr_today_bh = self._MakeBalanceHistCurrent(repr_prof)
        
        #adds r_key to today's BalanceHistory relationsChangedKeys
        #updates today's balance and rate for const and rep
        self._AddRelationToBalanceHists(rel, cons_today_bh, repr_today_bh)

        # # if saveProfile(), process user-modifyable fields
        # if change_request:
        #     for field in ('displayName', 'teeShirtSize'):
        #         if hasattr(change_request, field):
        #             val = getattr(change_request, field)
        #             if val:
        #                 setattr(rel, field, str(val))
        #                 #if field == 'teeShirtSize':
        #                 #    setattr(prof, field, str(val).upper())
        #                 #else:
        #                 #    setattr(prof, field, val)
        #                 rel.put()

        # return RelationForm
        return self._copyRelationToForm(rel)


    @endpoints.method(RelationForm, RelationForm, 
                path='relation',
                http_method='POST', 
                name='createRelation')
    #for each ER API instance on the gServer this createRelation method runs for that version
    #that version of the ER API Class is refered to by this class as self which is taken as an argument 

    #The second argument is request, which is an argument of the wrapping endpoints methhod, 
    #the first endpoints method argumrnt which in this case is of RelationForm Class model
    def createRelation(self, request): #self is each instance of the ElasticRepublic API on the server
        """Create new relation."""
        return self._doRelation(request)#Return the _doRelation method running on this instance of ER API


    @endpoints.method(UserIDForm, RelationForms,
                path='getUsersActiveRelations',
                http_method='POST',
                name='getUsersActiveRelations')
    def getUsersActiveRelations(self, request):
        """Query for a given users active relations."""

        #make sure asking user is signed in.
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        #get passed in user id
        user_id = request.userId 

        #get profile entity of user from Datastore
        prof = ndb.Key(Profile, user_id).get() 

        #if the userId is not in the system
        if not prof: 

            #return blank
            return RelationForms()

        #if the the userId is in the system
        else: 

            #get user's active relations keys
            rel_keys = prof.activeRelationsKeys 

            #get user's active relations entities from Datastore
            relations = ndb.get_multi(rel_keys) 

            # return individual RelationForm object per Relation
            return RelationForms(
                items=[self._copyRelationToForm(rela) \
                for rela in relations]
            )


# - - - Balance History objects - - - - - - - - - - - - - - - - - - -


    def _generateInitialBalanceHistory(self, profile_key):
        """Generate an Initial BalanceHistory."""
        
        #get today's date into memory
        todays_date = datetime.date.today()
        #create date in string format for key id 
        date_string = todays_date.isoformat()

        # #Generate BalanceHistory ID based on Profile key as ansestor
        # bh_id = BalanceHistory.allocate_ids(size=1, parent=profile_key)[0]
        
        #get BalanceHistory key from ID
        bh_key = ndb.Key(BalanceHistory, date_string, parent=profile_key)
             
        #add initial BalanceHistory entity
        bal_hist = BalanceHistory(
                key                  = bh_key,
                date                 = todays_date,
                eodBalance           = ONE_BALLOT, 
                DailyNetIncomingBFlow= 0,
        )

        #save users BalanceHistory entity to Datastore
        bal_hist.put() 

        return bh_key


    def _MakeBalanceHistCurrent(self, profile):
        """Make a profiles BalanceHistory current."""
        # Makes BalanceHistory current up to today
        # Prosesses UBI and money tax for each day
        # Assumes no Relation changes since last run

        # #query BalanceHistory ordered by datetime
        # q = BalanceHistory.all()
        # q.filter('__key__ >', last_seen_key)
        
        #read profile's last most recent Balance History key
        bh_key = profile.MostRecentBalanceHistoryKey
        #get mrbh object
        bal_hist = bh_key.get(use_cache=False, use_memcache=False)
        #get most recent BalanceHistory Date for User (mrbh_date)
        bh_date = bal_hist.date
        #put today's date into memory
        todays_date = datetime.date.today()  
        #put one day into memory
        one_day = datetime.timedelta(days=1)
        #read profile's mrbh end of day balance into memory
        bh_eodBalance = bal_hist.eodBalance
        #read profile's mrbh Daily Net Incoming Balllot Flow to memory
        bh_DailyNetIncomingBFlow = bal_hist.DailyNetIncomingBFlow

        #while date is less than and not equal to today
        while bh_date < todays_date:
            #Since this is programatically run prior to changing relations 
            #BalHist is always current up until previous day.
            #Today is not finalized until tomorrow.

            # relations_changed_this_day = mrbh.relationsChangedKeys != []

            # if relations_changed_this_day:
            #     raise endpoints.ForbiddenException(
            #         'Error: Make Current Failed. Todays Relation Changes wernt saves to Balance History')
            
            #create date in string format for key id 
            date_string = bh_date.isoformat() #This is weird, shoudn't it be after the increment below???

            #Increment date to next day so we can add a Balance History for that day
            bh_date += one_day
            
            # #Generate BalanceHistory ID based on most recent BH key as ansestor
            # bh_id = BalanceHistory.allocate_ids(size=1, parent=mrbh_key)[0]
            
            #Generate new BalanceHistory key from date string ID
            #use this key for next iteration
            bh_key = ndb.Key(BalanceHistory, date_string, parent=bh_key)
            
            #calculate the end of day balance
                            #yesterday's end of day balance
                            #\minus yesterday's tax
                            #\plus today's basic income
                            #\plus today's net incomeing ballotflow 
                            #(that's the same as yesterday's since no relations changed)
            bh_eodBalance = bh_eodBalance \
                          - (bh_eodBalance * MONEY_TAX_RATE) \
                          + BASIC_INCOME \
                          + bh_DailyNetIncomingBFlow 
                                   
            #Add BalanceHistory Entity
            bal_hist = BalanceHistory(
                key                   = bh_key,
                date                  = bh_date,
                eodBalance            = bh_eodBalance,
                DailyNetIncomingBFlow = bh_DailyNetIncomingBFlow,
                #relationsChangedKeys  = mrbh.relationsChangedKeys,
            )
            #save BalanceHistory entity to Datastore
            bal_hist.put() 

        return bal_hist

    def _copyBalanceHistoryToForm(self, bal_hist):
        """Copy all fields from BalanceHistory to BalanceHistoryForm."""
        bhf = BalanceHistoryForm()
        for field in bhf.all_fields():
            if hasattr(bal_hist, field.name):
                # convert Date to date string; just copy others
                if field.name.endswith('date'):
                    setattr(bhf, field.name, str(getattr(bal_hist, field.name)))
                elif field.name == "relationsChangedKeys":            
                    web_safe_keys = []
                    for key in getattr(bal_hist, 'relationsChangedKeys'):
                        web_safe_keys.append(key.urlsafe())
                    setattr(bhf, field.name, web_safe_keys)
                else:
                    setattr(bhf, field.name, getattr(bal_hist, field.name))
        bhf.check_initialized()
        return bhf


    @endpoints.method(message_types.VoidMessage, BalanceHistoryForms,
                path='getBalanceHistorysCreated',
                http_method='POST', 
                name='getBalanceHistorysCreated')
    def getBalanceHistorysCreated(self, request):
        """Return BalanceHistorys created by user."""
        # make sure user is authed
        user = endpoints.get_current_user()
        
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')
        
        user_id = getUserId(user)

        # create ancestor query for all key matches for this user
        balhists = BalanceHistory.query(ancestor=ndb.Key(Profile, user_id))
        
        #prof = ndb.Key(Profile, user_id).get()
        
        # return set of BalanceHistoryForm objects per BalanceHistory
        return BalanceHistoryForms(
            items=[self._copyBalanceHistoryToForm(balhist) for balhist in balhists]
        )

                
    def _AddRelationToBalanceHists(self, relation, const_bh, rep_bh):
        """Add a Relation to a profiles BalanceHistory."""
        #adds the new or changed Relation key to today's BalanceHistory for the profile as passed
        #Updates the DailyNetIncomingBFlow and eodBalance
        #Makecurrent was run first to return today's bh key
        #today's BH

        relation_key = relation.key

        relation_dailyRate = relation.dailyRate

        relation_dailyRate = relation.dailyRate

        #Append the relation key to todays balance history
        const_bh.relationsChangedKeys.append(relation_key)

        #Adjust the day's daily rate to include the new relation
        #Subtract for constituent
        const_bh.DailyNetIncomingBFlow -= relation_dailyRate

        #Begin Relation today by counting the daily rate towards today's balance
        #Subtract for constituent
        const_bh.eodBalance -= relation_dailyRate

        #save const profile to Datastore
        const_bh.put()


        #Append the relation key to todays balance history
        rep_bh.relationsChangedKeys.append(relation.key)

        #Adjust the day's daily rate to include the new relation
        #Add for Representive
        rep_bh.DailyNetIncomingBFlow += relation.dailyRate

        #Begin Relation today by counting the daily rate towards today's balance
        #Add for Representive
        rep_bh.eodBalance += relation.dailyRate

        #save const profile to Datastore
        rep_bh.put()

        return 

# - - - Profile objects - - - - - - - - - - - - - - - - - - -

    def _copyProfileToForm(self, prof):
        """Copy relevant fields from Profile to ProfileForm."""
        # copy relevant fields from ndb Profile to endpoints ProfileForm
        pf = ProfileForm()
        for field in pf.all_fields():
            if hasattr(prof, field.name):
                # convert t-shirt string to Enum; just copy others
                if field.name == 'teeShirtSize':
                    setattr(pf, field.name, getattr(TeeShirtSize, getattr(prof, field.name)))
                else:
                    setattr(pf, field.name, getattr(prof, field.name))
        pf.check_initialized()
        return pf


    def _getProfileFromUser(self):
        """Return user Profile from datastore, creating new one if non-existent."""
        # make sure user is authed
        user = endpoints.get_current_user()
        if not user:
            raise endpoints.UnauthorizedException('Authorization required')

        # get Profile from datastore
        user_id = getUserId(user)
        p_key = ndb.Key(Profile, user_id)
        profile = p_key.get(use_cache=False, use_memcache=False)
        
        # create new Profile if not there
        if not profile:

            #generate initial BalanceHistory 
            mrbhk = self._generateInitialBalanceHistory(p_key)
            
            #pupulate new ndb Profile entity
            profile = Profile(
                key = p_key,
                userId = user_id,
                displayName = user.nickname(),
                mainEmail= user.email(),
                teeShirtSize = str(TeeShirtSize.NOT_SPECIFIED),
                MostRecentBalanceHistoryKey = mrbhk,
            )
        
        #if profile exists make it's balance history current 
        #and update it's mosrt recent balance history key
        else:

            mrbh = self._MakeBalanceHistCurrent(profile)

            profile.MostRecentBalanceHistoryKey = mrbh.key

        #save Profile entity to Datastore 
        profile.put()    

        # return ndb Profile entity object
        return profile    


    def _doProfile(self, save_request=None):
        """Get user Profile and return to user, possibly updating it first."""
        # get user Profile
        prof = self._getProfileFromUser()

        # if saveProfile(), process user-modifyable fields
        if save_request:
            for field in ('displayName', 'teeShirtSize'):
                if hasattr(save_request, field):
                    val = getattr(save_request, field)
                    if val:
                        setattr(prof, field, str(val))
                        #if field == 'teeShirtSize':
                        #    setattr(prof, field, str(val).upper())
                        #else:
                        #    setattr(prof, field, val)
                        prof.put()

        # return ProfileForm
        return self._copyProfileToForm(prof)


    @endpoints.method(message_types.VoidMessage, ProfileForm,
                path='profile', 
                http_method='GET', 
                name='getProfile')
    def getProfile(self, request):
        """Return user profile."""
        return self._doProfile()


    @endpoints.method(ProfileMiniForm, ProfileForm,
                path='profile', 
                http_method='POST', 
                name='saveProfile')
    def saveProfile(self, request):
        """Update & return user profile."""
        return self._doProfile(request)


# registers API
api = endpoints.api_server([ElasticRepublicApi]) 
