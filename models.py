#!/usr/bin/env python

"""models.py

Elastic Republic server-side Python App Engine data & ProtoRPC models

"""

__author__ = 'mike.parziale@gmail.com (Michael Parziale)'

import httplib
import endpoints
from protorpc import messages
from google.appengine.ext import ndb


class Profile(ndb.Model):
    """Profile -- User profile object"""
    userId = ndb.StringProperty()
    displayName = ndb.StringProperty()
    mainEmail = ndb.StringProperty()
    teeShirtSize = ndb.StringProperty(default='NOT_SPECIFIED')
    MostRecentBalanceHistoryKey = ndb.KeyProperty(kind='BalanceHistory')
    activeRelationsKeys = ndb.KeyProperty(kind='Relation', repeated=True)


class ProfileMiniForm(messages.Message):
    """ProfileMiniForm -- update Profile form message"""
    displayName = messages.StringField(1)
    teeShirtSize = messages.EnumField('TeeShirtSize', 2)


class ProfileForm(messages.Message):
    """ProfileForm -- Profile outbound form message"""
    userId = messages.StringField(1)
    displayName = messages.StringField(2)
    mainEmail = messages.StringField(3)
    teeShirtSize = messages.EnumField('TeeShirtSize', 4)


class TeeShirtSize(messages.Enum):
    """TeeShirtSize -- t-shirt size enumeration value"""
    NOT_SPECIFIED = 1
    XS_M = 2
    XS_W = 3
    S_M = 4
    S_W = 5
    M_M = 6
    M_W = 7
    L_M = 8
    L_W = 9
    XL_M = 10
    XL_W = 11
    XXL_M = 12
    XXL_W = 13
    XXXL_M = 14
    XXXL_W = 15

class Relation(ndb.Model):
    """Relation -- Relation object"""
    name            = ndb.StringProperty(required=True)
    dailyRate       = ndb.IntegerProperty(required=True)
    contract        = ndb.StringProperty()
    constitUserId   = ndb.StringProperty()
    repUserId       = ndb.StringProperty(required=True)
    startDate       = ndb.DateTimeProperty()
    endDate         = ndb.DateTimeProperty()
    version         = ndb.IntegerProperty()


class RelationForm(messages.Message):
    """RelationForm -- Relation outbound form message"""
    name            = messages.StringField(1)
    dailyRate       = messages.IntegerField(2, variant=messages.Variant.INT32)
    contract        = messages.StringField(3)
    constitUserId   = messages.StringField(4)
    repUserId       = messages.StringField(5)  
    startDate       = messages.StringField(6)
    endDate         = messages.StringField(7)
    websafeKey      = messages.StringField(8)
    constitDisplayName  = messages.StringField(9)
    repDisplayName      = messages.StringField(10)
    oneTimeTransaction  = messages.BooleanField(11)

class RelationForms(messages.Message):
    """RelationForms -- multiple Relation outbound form message"""
    items = messages.MessageField(RelationForm, 1, repeated=True)


class BalanceHistory(ndb.Model):
    """BalanceHistory -- Balance History Datastore object"""
    date                  = ndb.DateProperty(required=True)
    eodBalance            = ndb.FloatProperty(required=True)
    DailyNetIncomingBFlow = ndb.IntegerProperty(required=True)
    relationsChangedKeys  = ndb.KeyProperty(kind='Relation', repeated=True)
    
class BalanceHistoryForm(messages.Message):
    """BalanceHistory -- User Balance History outbound form message"""
    date             = messages.StringField(1)
    eodBalance       = messages.FloatField(2)#end of day, required=True
    DailyNetIncomingBFlow = messages.IntegerField(3, variant=messages.Variant.INT32)
    relationsChangedKeys = messages.StringField(4, repeated=True) 

class BalanceHistoryForms(messages.Message):
    """BalanceHistoryForms -- multiple BalanceHistory outbound form message"""
    items = messages.MessageField(BalanceHistoryForm, 1, repeated=True)

class UserIDForm(messages.Message):
    """UserID-- inbound (single) string message"""
    userId = messages.StringField(1, required=True)

