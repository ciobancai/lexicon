from base import Provider as BaseProvider
import requests
import json

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'http://sandbox.rest.easydns.net'

    def authenticate(self):

        payload = self._get('/domain/{0}'.format(self.options['domain']))

        if not payload['data']['id']:
            raise StandardError('No domain found')

        self.domain_id = payload['data']['id']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'type': type,
            'domain': self.domain_id,
            'host': self._relative_name(name),
            'ttl': 300,
            'prio': 0,
            'rdata': content
        }
        payload = {}
        try:
            payload = self._put('/zones/records/add/{0}/{1}'.format(self.domain_id, type), record)
        except requests.exceptions.HTTPError, e:
            if e.response.status_code == 400:
                payload = {}

                # http 400 is ok here, because the record probably already exists
        print 'create_record: {0}'.format(True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}

        payload = self._get('/zones/records/all/{0}'.format(self.domain_id))
        records = []
        for record in payload['data']:
            processed_record = {
                'type': record['type'],
                'name': "{0}.{1}".format(record['host'], record['domain']),
                'ttl': record['ttl'],
                'content': record['rdata'],
                'id': record['id']
            }
            records.append(processed_record)

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            records = [record for record in records if record['name'] == self._full_name(name)]
        if content:
            records = [record for record in records if record['content'] == content]

        print 'list_records: {0}'.format(records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'ttl': 300
        }
        if type:
            data['type'] = type
        if name:
            data['host'] = self._relative_name(name),
        if content:
            data['rdata'] = content

        payload = self._post('/zones/records/{0}'.format(identifier), data)

        print 'update_record: {0}'.format(True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, name, content)
            print records
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise StandardError('Record identifier could not be found.')
        payload = self._delete('/zones/records/{0}/{1}'.format(self.domain_id, identifier))

        # is always True at this point, if a non 200 response is returned an error is raised.
        print 'delete_record: {0}'.format(True)
        return True


    # Helpers


    def _full_name(self, record_name):
        record_name = record_name.rstrip('.') # strip trailing period from fqdn if present
        #check if the record_name is fully specified
        if not record_name.endswith(self.options['domain']):
            record_name = "{0}.{1}".format(record_name, self.options['domain'])
        return record_name

    def _relative_name(self, record_name):
        record_name = record_name.rstrip('.') # strip trailing period from fqdn if present
        #check if the record_name is fully specified
        if record_name.endswith(self.options['domain']):
            record_name = record_name[:-len(self.options['domain'])]
            record_name = record_name.rstrip('.')
        return record_name

    def _get(self, url='/', query_params={}):
        return self._request('GET', url, query_params=query_params)

    def _post(self, url='/', data={}, query_params={}):
        return self._request('POST', url, data=data, query_params=query_params)

    def _put(self, url='/', data={}, query_params={}):
        return self._request('PUT', url, data=data, query_params=query_params)

    def _delete(self, url='/', query_params={}):
        return self._request('DELETE', url, query_params=query_params)

    def _request(self, action='GET',  url='/', data={}, query_params={}):

        query_params['format'] = 'json'
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        default_auth = (self.options['auth_username'], self.options.get('auth_password') or self.options.get('auth_token'))

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
