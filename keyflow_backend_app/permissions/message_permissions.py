from rest_framework.permissions import BasePermission
from rest_framework import permissions
from ..models.message import Message
from rest_framework.response import Response
from rest_framework import status

class IsSenderOrRecipient(BasePermission):
    """
    Custom permission to only allow users to access messages where they are the sender or recipient.
    """

    def has_permission(self, request, view):
        # Allow access only to authenticated users
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Check if the user is the sender or recipient of the message
        return obj.sender == request.user or obj.recipient == request.user

#-----MESSAGE PERMISSIONS-----#
#Create a permission that only allows a message to be deleted if the user is the sender or recipient
class MessageDeletePermission(permissions.BasePermission):
    
        def has_permission(self, request, view):
            if request.method  == 'DELETE':
                #retrieve primarky key from url 
                url_id = view.kwargs.get('pk', None) #id in the url converted to int
    
                request_id = request.user.id #id of the user making the request
                #request.data.get('rental_property')
                #create variable for request body
                request_body_message = url_id
    
                #retrieve unit object from  request_body_property variable
                message_object = Message.objects.get(id=request_body_message)
                message_sender_id = message_object.sender.id #id of the user who owns the property
                message_recipient_id = message_object.recipient.id #id of the user who owns the property
    
                #confirm the id and unit's user id match
                if (message_sender_id != int(request_id) and message_recipient_id != int(request_id)):
                    return Response({"message": "You cannot delete a message that you did not send"}, status=status.HTTP_401_UNAUTHORIZED)
                return True # grant access otherwise
            return True # grant access otherwise

#Create permission that only allows owners to send messages to thier tenants and tenants to only send messages to their owners
class MessageCreatePermission(permissions.BasePermission):
        def has_permission(self, request, view):
            if request.method  == 'POST':
                #retrieve primarky key from url 
                # url_id = view.kwargs.get('pk', None) #id in the url converted to int
    
                request_id = request.user.id #id of the user making the request
                #request.data.get('rental_property')
                #create variable for request body
                request_body_sender = request.data.get('sender')
                request_body_recipient = request.data.get('recipient')
    
                #retrieve unit object from  request_body_property variable
                # message_object = Message.objects.get(id=request_body_message)
                # message_sender_id = message_object.sender.id #id of the user who owns the property
                # message_recipient_id = message_object.recipient.id #id of the user who owns the property
    
                #confirm the id and unit's user id match
                if (request_body_sender != int(request_id) and request_body_recipient != int(request_id)):
                    return Response({"message": "You cannot send a message to a user that you are not associated with"}, status=status.HTTP_401_UNAUTHORIZED)
                return True # grant access otherwise
            return True # grant access otherwise