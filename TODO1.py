
def _RelationBeginning():

	#If the Relation with this name doesn't exist between these two people:

		#Create new Relation 

		#


def _RelationChanging(websaferelationkey, ):	

	#If the Relation with this name already exists between these two people
	#(do to update from websafe Relation key ref) and there is a 
	#change to rate or contract:
		
		#Create new Relation with prev Relation's key as Ansestor.
		
		#Pass name, constitUserId, and repUserId from child.
		
		#From user Add new dailyRate and contract. 
		
		#Set todays date as startdate on child.
		
		#Add today's date as end date on ansestor.
		
		#increment version number of ansestor Relation and save in child Relation. 
		
		#Save both ansestor and child Relation to Datastore.
		
		#Remove ansestor key from const and rep profiles ActiveRelations.
		
		#Append child key to const and rep profiles ActiveRelations.

def _RelationEnding([websaferelationkey, relation_ending=None]):

	#If the Relation with this name is ending or new rate is 0:

		#Add today's date as end date on ansestor.
	
		#Save ancestor Relation.
	
		#Remove ansestor key from const and rep profiles ActiveRelations.



		