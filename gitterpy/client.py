import requests as r

from gitterpy.const import GITTER_BASE_URL, GITTER_STREAM_URL
from gitterpy.errors import GitterItemsError, GitterRoomError, GitterTokenError


class BaseApi:
    def __init__(self, token):
        if not token:
            raise GitterTokenError
        self.token = token
        self.headers = {'Authorization': 'Bearer ' + self.token}

    def stream_request(self, method, api, **kwargs):
        url = GITTER_STREAM_URL + api
        return method(url, headers=self.headers, stream=True, **kwargs).json()

    def request_process(self, method, api, **kwargs):
        url = GITTER_BASE_URL + api
        return method(url, headers=self.headers, **kwargs).json()

    def get(self, api, **kwargs):
        return self.request_process(r.get, api, **kwargs)

    def post(self, api, **kwargs):
        return self.request_process(r.post, api, **kwargs)

    def put(self, api, **kwargs):
        return self.request_process(r.put, api, **kwargs)

    def delete(self, api, **kwargs):
        return self.request_process(r.delete, api, **kwargs)

    def stream_get(self, api, **kwargs):
        return self.stream_request(r.get, api, **kwargs)

    def check_auth(self):
        return self.get('user')

    @property
    def get_user_id(self):
        return self.check_auth()[0]['id']

    @property
    def rooms_list(self):
        return self.get('rooms')

    @property
    def groups_list(self):
        return self.get('groups')

    def find_by_room_name(self, name):
        room_id = ''
        for x in self.rooms_list:
            if x['name'] == name:
                room_id = x['id']
        return room_id

    def set_user_url(self, param):
        return 'user/{}/{}'.format(self.get_user_id, param)

    def set_message_url(self, param):
        return 'rooms/{}/chatMessages'.format(param)

    def set_user_items_url(self, room_name):
        return 'user/{}/rooms/{}/unreadItems'.format(
            self.get_user_id,
            self.find_by_room_name(room_name)
        )

    def get_and_update_msg_url(self, room_name, message_id):
        room_id = self.find_by_room_name(room_name)
        return 'rooms/{}/chatMessages/{}'.format(room_id, message_id)


class Auth(BaseApi):
    @property
    def get_my_id(self):
        user_id = self.check_auth()[0]['id']
        name = self.check_auth()[0]['username']
        return {'name': name, 'user_id': user_id}


class Groups(BaseApi):
    @property
    def list(self):
        return self.groups_list


class Rooms(BaseApi):
    def grab_room(self, uri_name):
        return self.post('rooms', data={'uri': uri_name})

    def join(self, room_name):
        try:
            room_id = self.grab_room(room_name)['id']
            api_meth = 'user/{}/rooms'.format(self.get_user_id)
            return self.post(api_meth, data={'id': room_id})
        except KeyError:
            return 'Room {} not found'.format(room_name)

    def leave(self, room_name):
        room_id = self.find_by_room_name(room_name)
        user_id = self.get_user_id
        if room_id:
            api_meth = 'rooms/{}/users/{}'.format(room_id, user_id)
            return self.delete(api_meth)
        else:
            raise GitterRoomError(room_name)

    def update(self, room_name, topic, no_index=None, tags=None):
        api_meth = 'rooms/{}'.format(self.find_by_room_name(room_name))
        return self.put(
            api_meth,
            data={'topic': topic, 'noindex': no_index, 'tags': tags}
        )

    def delete_room(self, room_name):
        api_meth = 'rooms/{}'.format(self.find_by_room_name(room_name))
        return self.delete(api_meth)

    def sub_resource(self, room_name):
        api_meth = 'rooms/{}/users'.format(self.find_by_room_name(room_name))
        return self.get(api_meth)


class Messages(BaseApi):
    def list(self, room_name):
        room_id = self.find_by_room_name(room_name)
        return self.get(
            self.set_message_url(room_id)
        )

    def send(self, room_name, text='GitterHQPy test message'):
        room_id = self.find_by_room_name(room_name)
        return self.post(
            self.set_message_url(room_id),
            data={'text': text}
        )

    def get_message(self, room_name, message_id):
        api_meth = self.get_and_update_msg_url(room_name, message_id)
        return self.get(api_meth)


class User(BaseApi):
    @property
    def current_user(self):
        return self.check_auth()

    @property
    def sub_resource(self):
        return self.get(
            self.set_user_url('rooms')
        )

    def unread_items(self, room_name):
        api_meth = self.set_user_items_url(room_name)
        return self.get(api_meth)

    def mark_as_read(self, room_name):
        """
        message_ids return an array
        with unread message ids ['131313231', '323131']
        """
        api_meth = self.set_user_items_url(room_name)
        message_ids = self.unread_items(room_name).get('chat')
        if message_ids:
            return self.post(api_meth, data={'chat': message_ids})
        else:
            raise GitterItemsError(room_name)

    @property
    def orgs(self):
        return self.get(
            self.set_user_url('orgs')
        )

    @property
    def repos(self):
        return self.get(
            self.set_user_url('repos')
        )

    @property
    def channels(self):
        return self.get(
            self.set_user_url('channels')
        )


class Stream(BaseApi):
    def chat_messages(self, room_name):
        room_id = self.find_by_room_name(room_name)
        return self.stream_get(
            self.set_message_url(room_id)
        )

    def events(self, room_name):
        room_id = self.find_by_room_name(room_name)
        api_meth = 'rooms/{}/events'.format(room_id)
        return self.stream_get(api_meth)


class GitterClient(BaseApi):
    def __init__(self, token=None):
        super().__init__(token)
        self.auth = Auth(token)
        self.groups = Groups(token)
        self.rooms = Rooms(token)
        self.messages = Messages(token)
        self.user = User(token)
        self.stream = Stream(token)
