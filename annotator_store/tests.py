import json
try:
    # python 3
    from unittest.mock import Mock, patch
except ImportError:
    # python 2.7
    from mock import Mock, patch
import uuid
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, AnonymousUser
from django.core.urlresolvers import reverse, resolve
from django.test import TestCase
from django.test.utils import override_settings
try:
    from guardian.shortcuts import remove_perm
except ImportError:
    remove_perm = None
import pytest
import six

from .models import Annotation, ANNOTATION_OBJECT_PERMISSIONS

if ANNOTATION_OBJECT_PERMISSIONS:
    # annotation group is only defined when permissions are enabled
    from .models import AnnotationGroup


# TODO: how to test functionality when per-object permissions are
# turned off and/or guardian is not installed?
# - could this be tested via travis-ci env settings?





class AnnotationTestCase(TestCase):
    fixtures = ['test_annotation_data.json']

    # test annotation data based on annotatorjs documentation
    # http://docs.annotatorjs.org/en/v1.2.x/annotation-format.html
    annotation_data = {
        "id": "39fc339cf058bd22176771b3e3187329",
        "annotator_schema_version": "v1.0",
        "created": "2011-05-24T18:52:08.036814",
        "updated": "2011-05-26T12:17:05.012544",
        "text": "A note I wrote",
        "quote": "the text that was annotated",
        "uri": "http://example.com",
        "ranges": [
            {
               "start": "/p[69]/span/span",
               "end": "/p[70]/span/span",
               "startOffset": 0,
               "endOffset": 120
           }
        ],
        # "user": "alice",
        "consumer": "annotateit",
        "tags": ["review", "error"],
        "permissions": {
            # "read": ["group:__world__"],
            "read": ["testuser"],
            "admin": [],
            "update": [],
            "delete": []
        },
        'related_pages': [
            'http://testpid.co/ark:/1234/11',
            'http://testpid.co/ark:/1234/22',
            'http://testpid.co/ark:/1234/qq'
        ]
        # add sample extra annotation data
    }

    def setUp(self):
        # use mock to simulate django httprequest
        self.mockrequest = Mock(user=get_user_model().objects.get(username='testuser'))
        self.mockrequest.body = six.b(json.dumps(self.annotation_data))

    def test_create_from_request(self):
        note = Annotation.create_from_request(self.mockrequest)
        self.assertEqual(self.annotation_data['text'], note.text)
        self.assertEqual(self.annotation_data['quote'], note.quote)
        self.assertEqual(self.annotation_data['uri'], note.uri)
        self.assert_('ranges' in note.extra_data)
        self.assertEqual(self.annotation_data['ranges'][0]['start'],
            note.extra_data['ranges'][0]['start'])
        # this behavior changes when permissions are enabled
        if not ANNOTATION_OBJECT_PERMISSIONS:
            self.assert_('permissions' in note.extra_data)

        # create from request with user specified
        user = get_user_model().objects.get(username='testuser')
        self.mockrequest.user = user
        note = Annotation.create_from_request(self.mockrequest)
        self.assertEqual(user, note.user)

    def test_info(self):
        note = Annotation.create_from_request(self.mockrequest)
        note.save()  # save so created/updated will get set
        info = note.info()
        fields = ['id', 'annotator_schema_version', 'created', 'updated',
            'text', 'quote', 'uri', 'user', 'ranges', 'permissions']
        # test that expected fields are present
        for f in fields:
            self.assert_(f in info)
        # test that dates are in isoformat
        self.assertEqual(info['created'], note.created.isoformat())
        self.assertEqual(info['updated'], note.updated.isoformat())

        # associate note with a user
        user = get_user_model().objects.get(username='testuser')
        note.user = user
        info = note.info()
        self.assertEqual(user.username, info['user'])

        # TODO assert includes permissions dict when appropriate

    def test_last_created_time(self):
        # test custom queryset methods
        Annotation.objects.all().delete()  # delete fixture annotations
        self.assertEqual(None, Annotation.objects.all().last_created_time())

        note = Annotation.create_from_request(self.mockrequest)
        note.save()  # save so created/updated will get set
        self.assertEqual(note.created,
                         Annotation.objects.all().last_created_time())

    def last_updated_time(self):
        Annotation.objects.all().delete()  # delete fixture annotations
        self.assertEqual(None, Annotation.objects.all().last_updated_time())

        note = Annotation.create_from_request(self.mockrequest)
        note.save()  # save so created/updated will get set
        self.assertEqual(note.updated,
                         Annotation.objects.all().last_updated_time())

    def test_related_pages(self):
        note = Annotation.create_from_request(self.mockrequest)
        self.assertEqual(len(self.annotation_data['related_pages']),
            len(note.related_pages))
        for idx in range(len(self.annotation_data['related_pages'])):
            self.assertEqual(self.annotation_data['related_pages'][idx],
                note.related_pages[idx])
            self.assertEqual(self.annotation_data['related_pages'][idx],
                note.extra_data['related_pages'][idx])

        note = Annotation()
        self.assertEqual(None, note.related_pages)

    def test_handle_extra_data(self):
        # test handle extra data method to check it is called appropriately
        def test_handler(obj, data, request):
            obj.quote += ' mischief managed!'
            return {'foo': 'bar'}

        with patch.object(Annotation, 'handle_extra_data', new=test_handler):
            # should be called when creating a new object
            note = Annotation.create_from_request(self.mockrequest)
            assert note.quote.endswith('mischief managed!')
            assert note.extra_data == {'foo': 'bar'}

            # should be called when updating objects
            note.update_from_request(self.mockrequest)
            assert note.quote.endswith('mischief managed!')
            assert note.extra_data == {'foo': 'bar'}


@pytest.mark.skipif(not ANNOTATION_OBJECT_PERMISSIONS,
                    reason="can only be tested when permissions are enabled")
class AnnotationPermissionsTestCase(TestCase):
    fixtures = ['test_annotation_data.json']

    annotation_data = AnnotationTestCase.annotation_data

    def setUp(self):
        # use mock to simulate django httprequest
        self.mockrequest = Mock(user=get_user_model().objects.get(username='testuser'))
        self.mockrequest.body = six.b(json.dumps(self.annotation_data))

    def test_visible_to(self):
        # delete fixture annotations and test only those created here
        Annotation.objects.all().delete()

        testuser = get_user_model().objects.get(username='testuser')
        testadmin = get_user_model().objects.get(username='testsuper')

        Annotation.objects.create(user=testuser, text='foo')
        Annotation.objects.create(user=testuser, text='bar')
        Annotation.objects.create(user=testuser, text='baz')
        Annotation.objects.create(user=testadmin, text='qux')

        self.assertEqual(3, Annotation.objects.visible_to(testuser).count())
        self.assertEqual(4, Annotation.objects.visible_to(testadmin).count())

    def test_update_from_request(self):
        # create test note to update
        note = Annotation(text="Here's the thing", quote="really",
            extra_data=json.dumps({'sample data': 'foobar'}))
        note.save()

        # permissions check requires a real user
        user = get_user_model().objects.get(username='testuser')
        self.mockrequest.user = user

        with patch.object(note, 'db_permissions') as mock_db_perms:
            note.update_from_request(self.mockrequest)
            self.assertEqual(self.annotation_data['text'], note.text)
            self.assertEqual(self.annotation_data['quote'], note.quote)
            self.assertEqual(self.annotation_data['uri'], note.uri)
            self.assert_('ranges' in note.extra_data)
            self.assertEqual(self.annotation_data['ranges'][0]['start'],
                note.extra_data['ranges'][0]['start'])
            self.assert_('permissions' not in note.extra_data)
            # existing extra data should no longer present
            self.assert_('sample data' not in note.extra_data)

            # testuser does not have admin on this annotation;
            # permissions should not be updated
            mock_db_perms.assert_not_called()

            # give user admin permission and update again
            note.assign_permission('admin_annotation', user)
            note.update_from_request(self.mockrequest)
            mock_db_perms.assert_called_with(self.annotation_data['permissions'])

    def test_user_permissions(self):
        # annotation user/owner automatically gets permissions
        user = get_user_model().objects.get(username='testuser')
        note = Annotation.create_from_request(self.mockrequest)
        note.user = user
        note.save()

        user_perms = note.user_permissions()
        self.assertEqual(4, user_perms.count())
        self.assert_(user_perms.filter(user=user,
                                       permission__codename='view_annotation')
                               .exists())
        self.assert_(user_perms.filter(user=user,
                                       permission__codename='change_annotation')
                               .exists())
        self.assert_(user_perms.filter(user=user,
                                       permission__codename='delete_annotation')
                               .exists())
        self.assert_(user_perms.filter(user=user,
                                       permission__codename='admin_annotation')
                               .exists())

        note.save()
        # saving again shouldn't duplicate the permissions
        self.assertEqual(4, note.user_permissions().count())

    def test_db_permissions(self):
        note = Annotation.create_from_request(self.mockrequest)
        note.save()
        # get some users and groups to work with
        user = get_user_model().objects.get(username='testuser')
        group1 = AnnotationGroup.objects.create(name='foo')
        group2 = AnnotationGroup.objects.create(name='foobar')

        note.db_permissions({
            'read': [user.username, group1.annotation_id,
                     group2.annotation_id],
            'update': [user.username, group1.annotation_id],
            'delete': [user.username]
        })

        # inspect the db permissions created

        # should be two total user permissions, one to view and one to change
        user_perms = note.user_permissions()
        self.assertEqual(3, user_perms.count())
        self.assert_(user_perms.filter(user=user,
                                       permission__codename='view_annotation')
                               .exists())
        self.assert_(user_perms.filter(user=user,
                                       permission__codename='change_annotation')
                               .exists())
        self.assert_(user_perms.filter(user=user,
                                       permission__codename='delete_annotation')
                               .exists())

        # should be three total group permissions
        group_perms = note.group_permissions()
        self.assertEqual(3, group_perms.count())
        self.assert_(group_perms.filter(group=group1,
                                        permission__codename='view_annotation')
                                .exists())
        self.assert_(group_perms.filter(group=group1,
                                        permission__codename='change_annotation')
                                .exists())
        self.assert_(group_perms.filter(group=group2,
                                        permission__codename='view_annotation')
                                .exists())

        # updating the permissions for the same note should
        # remove permissions that no longer apply
        note.db_permissions({
            'read': [user.username, group1.annotation_id],
            'update': [user.username],
            'delete': []
        })

        # counts should reflect the changes
        user_perms = note.user_permissions()
        self.assertEqual(2, user_perms.count())
        group_perms = note.group_permissions()
        self.assertEqual(1, group_perms.count())

        # permissions created before should be gone
        self.assertFalse(user_perms.filter(user=user,
                                           permission__codename='delete_annotation')
                                   .exists())
        self.assertFalse(group_perms.filter(group=group1,
                                            permission__codename='change_annotation')
                                    .exists())
        self.assertFalse(group_perms.filter(group=group2,
                                            permission__codename='view_annotation')
                                    .exists())

        # invalid group/user should not error
        note.db_permissions({
            'read': ['bogus', 'group:666', 'group:foo'],
            'update': ['group:__world__'],
            'delete': []
        })

        self.assertEqual(0, note.user_permissions().count())
        self.assertEqual(0, note.group_permissions().count())


    def test_permissions_dict(self):
        note = Annotation.create_from_request(self.mockrequest)
        note.save()
        # get some users and groups to work with
        user = get_user_model().objects.get(username='testuser')
        group1 = AnnotationGroup.objects.create(name='foo')
        group2 = AnnotationGroup.objects.create(name='foobar')

        perms = {
            'read': [user.username, group1.annotation_id,
                     group2.annotation_id],
            'update': [user.username, group1.annotation_id],
            'delete': [user.username],
            'admin': []
        }
        # test round-trip: convert to db permissions and then back
        note.db_permissions(perms)
        self.assertEqual(perms, note.permissions_dict())

        perms = {
            'read': [user.username, group1.annotation_id],
            'update': [user.username],
            'delete': [],
            'admin': []
        }
        note.db_permissions(perms)
        self.assertEqual(perms, note.permissions_dict())

        perms = {
            'read': [],
            'update': [],
            'delete': [],
            'admin': []
        }
        note.db_permissions(perms)
        self.assertEqual(perms, note.permissions_dict())



@override_settings(AUTHENTICATION_BACKENDS=('django.contrib.auth.backends.ModelBackend',))
class AnnotationViewsTest(TestCase):
    fixtures = ['test_annotation_data.json']

    user_credentials = {
        'user': {'username': 'testuser', 'password': 'testing'},
        'superuser': {'username': 'testsuper', 'password': 'superme'}
    }

    def setUp(self):
        # annotation that belongs to testuser
        self.user_note = Annotation.objects \
            .get(user__username=self.user_credentials['user']['username'])
        # annotation that belongs to superuser
        self.superuser_note = Annotation.objects \
            .get(user__username=self.user_credentials['superuser']['username'])
        # NOTE: currently fixture only has one note for each user.
        # If that changes, use filter(...).first()

        # run the updated save method to grant author access
        for note in Annotation.objects.all():
            note.save()

    def test_api_index(self):
        resp = self.client.get(reverse('annotation-api:index'))
        self.assertEqual('application/json', resp['Content-Type'])
        # expected fields in the output
        data = json.loads(resp.content.decode())
        for f in ['version', 'name']:
            self.assert_(f in data)

    def test_list_annotations(self):
        notes = Annotation.objects.all()
        user_notes = notes.filter(user__username='testuser')

        # anonymous user should see no notes
        resp = self.client.get(reverse('annotation-api:annotations'))
        self.assertEqual('application/json', resp['Content-Type'])
        data = json.loads(resp.content.decode())
        self.assertEqual(0, len(data))

        # log in as a regular user
        self.client.login(**self.user_credentials['user'])
        resp = self.client.get(reverse('annotation-api:annotations'))
        data = json.loads(resp.content.decode())

        if ANNOTATION_OBJECT_PERMISSIONS:
            # when per-object permissions are enabled, notes should
            # automatically be filtered to this user
            self.assertEqual(user_notes.count(), len(data))
            self.assertEqual(data[0]['id'], str(user_notes[0].id))
        else:
            # without per-object permissions, user won't see anything
            assert len(data) == 0

            # add view permission and search again - should see all notes
            view_perm = Permission.objects.get(codename='view_annotation')
            testuser = get_user_model().objects.get(username='testuser')
            testuser.user_permissions.add(view_perm)
            resp = self.client.get(reverse('annotation-api:annotations'))
            data = json.loads(resp.content.decode())
            assert len(data) == notes.count()

        # log in as superuser
        self.client.login(**self.user_credentials['superuser'])
        resp = self.client.get(reverse('annotation-api:annotations'))
        data = json.loads(resp.content.decode())
        # all notes user should be listed
        self.assertEqual(notes.count(), len(data))
        self.assertEqual(data[0]['id'], str(notes[0].id))
        self.assertEqual(data[1]['id'], str(notes[1].id))

        # test group permissions
        if ANNOTATION_OBJECT_PERMISSIONS:
            # group permissions are only enabled when per-object permissions
            # are turned on

            self.client.login(**self.user_credentials['user'])
            # reassign testuser notes to superuser
            superuser_name = self.user_credentials['superuser']['username']
            user = get_user_model().objects.get(username='testuser')
            superuser = get_user_model().objects.get(username=superuser_name)
            for note in user_notes:
                note.user = superuser
                note.save()
                # manually remove the permission, since the model
                # does not expect annotation owners to change
                if remove_perm:
                    remove_perm('view_annotation', user, note)

            group = AnnotationGroup.objects.create(name='annotation group')
            group.user_set.add(user)
            group.save()

            resp = self.client.get(reverse('annotation-api:annotations'))
            data = json.loads(resp.content.decode())
            # user should not have access to any notes
            self.assertEqual(0, len(data))

            # update first note with group read permissions
            user_notes[0].db_permissions({'read': [group.annotation_id]})

            resp = self.client.get(reverse('annotation-api:annotations'))
            data = json.loads(resp.content.decode())
            # user should have access to any notes by group permissiosn
            self.assertEqual(1, len(data))
            self.assertEqual(data[0]['id'], str(notes[0].id))

    def test_create_annotation(self):
        url = reverse('annotation-api:annotations')
        resp = self.client.post(url,
            data=json.dumps(AnnotationTestCase.annotation_data),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        # not logged in - should not be allowed
        self.assertEqual(401, resp.status_code,
            'should return 401 Unauthorized on anonymous attempt to create annotation, got %s' \
            % resp.status_code)

        # log in as a regular user
        self.client.login(**self.user_credentials['user'])
        resp = self.client.post(url,
            data=json.dumps(AnnotationTestCase.annotation_data),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(303, resp.status_code,
            'should return 303 See Other on succesful annotation creation, got %s' \
            % resp.status_code)
        # get view information
        location = resp['Location']
        # change from django 1.8 to 1.9 - http://testserver no longer included
        if location.startswith('http://testserver'):
            location = location[len('http://testserver'):]
        view = resolve(location)
        self.assertEqual('annotation-api:view', '%s:%s' % (view.namespaces[0], view.url_name),
            'successful create should redirect to annotation view')

        # lookup the note and confirm values were set from request
        note = Annotation.objects.get(id=view.kwargs['id'])
        self.assertEqual(AnnotationTestCase.annotation_data['text'],
            note.text, 'annotation content should be set from request data')

    def test_get_annotation(self):
        # not logged in - should be denied
        resp = self.client.get(reverse('annotation-api:view',
            kwargs={'id': self.user_note.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # simulate ajax request to get 401, otherwise returns 302
        # with redirect to login page
        self.assertEqual(401, resp.status_code,
            'should return 401 Unauthorized on anonymous attempt to view annotation, got %s' \
            % resp.status_code)

        # log in as a regular user
        self.client.login(**self.user_credentials['user'])
        testuser = get_user_model().objects.get(username='testuser')
        view_perm = Permission.objects.get(codename='view_annotation')

        # if per-object permissions are not enabled, grant view permission
        if not ANNOTATION_OBJECT_PERMISSIONS:
            testuser.user_permissions.add(view_perm)

        resp = self.client.get(reverse('annotation-api:view',
            kwargs={'id': self.user_note.id}))
        self.assertEqual('application/json', resp['Content-Type'])
        # check a few fields in the data
        data = json.loads(resp.content.decode())
        self.assertEqual(str(self.user_note.id), data['id'])
        self.assertEqual(self.user_note.text, data['text'])
        self.assertEqual(self.user_note.created.isoformat(), data['created'])

        # logged in but trying to view someone else's note

        # if per-object permissions are not enabled, remove view permission
        if not ANNOTATION_OBJECT_PERMISSIONS:
            testuser.user_permissions.remove(view_perm)

        resp = self.client.get(reverse('annotation-api:view',
            kwargs={'id': self.superuser_note.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(403, resp.status_code,
            'should return 403 Forbidden on attempt to view other user\'s annotation, got %s' \
            % resp.status_code)

        # log in as a superuser - can view other user's notes
        self.client.login(**self.user_credentials['superuser'])
        resp = self.client.get(reverse('annotation-api:view',
            kwargs={'id': self.user_note.id}))
        data = json.loads(resp.content.decode())
        self.assertEqual(str(self.user_note.id), data['id'])

        # test 404
        resp = self.client.get(reverse('annotation-api:view', kwargs={'id': uuid.uuid4()}))
        self.assertEqual(404, resp.status_code)

    def test_update_annotation(self):
        # login/permission checking is common to get/update/delete views, but
        # just to be sure nothing breaks, duplicate those
        url = reverse('annotation-api:view', kwargs={'id': self.user_note.id})
        resp = self.client.put(url,
            data=json.dumps(AnnotationTestCase.annotation_data),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(401, resp.status_code,
            'expected 401 Unauthorized on anonymous attempt to update annotation, got %s' \
            % resp.status_code)

        # log in as a regular user
        self.client.login(**self.user_credentials['user'])
        view_perm = Permission.objects.get(codename='view_annotation')
        update_perm = Permission.objects.get(codename='change_annotation')

        # if per-object permissions are enabled, by default user has
        # update access to their own annotations; when testing with
        # normal django permissions, give the user view & change permissions
        if not ANNOTATION_OBJECT_PERMISSIONS:
            testuser = get_user_model().objects.get(username='testuser')
            testuser.user_permissions.add(view_perm)
            testuser.user_permissions.add(update_perm)

        resp = self.client.put(url,
            data=six.b(json.dumps(AnnotationTestCase.annotation_data)),
            content_type='application/json',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(303, resp.status_code,
            'expected 303 See Other on succesful annotation update, got %s' \
            % resp.status_code)
        # get view information
        assert url in resp['Location']
        # get a fresh copy from the db and check values
        n1 = Annotation.objects.get(id=self.user_note.id)
        self.assertEqual(AnnotationTestCase.annotation_data['text'],
            n1.text)
        self.assertEqual(AnnotationTestCase.annotation_data['quote'],
            n1.quote)
        self.assertEqual(AnnotationTestCase.annotation_data['ranges'],
            n1.extra_data['ranges'])

        # if per-object permissions are enabled, by default user ONLY has
        # update access to their own annotations; when testing with
        # normal django permissions, remove blanket change permissions
        if not ANNOTATION_OBJECT_PERMISSIONS:
            testuser.user_permissions.remove(update_perm)

        # logged in but trying to edit someone else's note
        resp = self.client.put(reverse('annotation-api:view',
            kwargs={'id': self.superuser_note.id}),
            data=json.dumps(AnnotationTestCase.annotation_data),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(403, resp.status_code,
            'expected 403 Forbidden on attempt to view update user\'s annotation, got %s' \
            % resp.status_code)

        # log in as a superuser - can edit other user's notes
        self.client.login(**self.user_credentials['superuser'])
        data = {'text': 'this is a super annotation!'}
        resp = self.client.put(reverse('annotation-api:view',
            kwargs={'id': self.user_note.id}),
            data=json.dumps(data),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        # note should be updated
        n1 = Annotation.objects.get(id=self.user_note.id)
        self.assertEqual(data['text'], n1.text)

        # test 404
        resp = self.client.put(reverse('annotation-api:view',
            kwargs={'id': str(uuid.uuid4())}),
            data=json.dumps(AnnotationTestCase.annotation_data),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(404, resp.status_code)

    def test_delete_annotation(self):
        # login/permission checking is common to get/update/delete views, but
        # just to be sure nothing breaks, duplicate those
        url = reverse('annotation-api:view', kwargs={'id': self.user_note.id})
        resp = self.client.delete(url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(401, resp.status_code,
            'should return 401 Unauthorized on anonymous attempt to delete annotation, got %s' \
            % resp.status_code)

        # log in as a regular user
        self.client.login(**self.user_credentials['user'])
        # if per-object permissions are enabled, users can delete their own
        # annotations; otherwise, simulate by giving blanket delete
        # (needs view perm also - must be able to view an annotation to delete it)
        if not ANNOTATION_OBJECT_PERMISSIONS:
            view_perm = Permission.objects.get(codename='view_annotation')
            delete_perm = Permission.objects.get(codename='delete_annotation')
            testuser = get_user_model().objects.get(username='testuser')
            testuser.user_permissions.add(view_perm)
            testuser.user_permissions.add(delete_perm)

        resp = self.client.delete(url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(204, resp.status_code,
            'expected 204 No Content for succesful annotation deletion, got %s' %\
            resp.status_code)
        self.assertEqual(six.b(''), resp.content,
            'deletion response should have no content')

        # attempt to delete other user's note

        # if per-object permissions are not enabled, remove delete perm
        if not ANNOTATION_OBJECT_PERMISSIONS:
            testuser.user_permissions.remove(delete_perm)

        url = reverse('annotation-api:view', kwargs={'id': self.superuser_note.id})
        resp = self.client.delete(url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(403, resp.status_code,
            'expected 403 Forbidden on attempt to delete another user\'s annotation, got %s' \
            % resp.status_code)

        # not explicitly tested: superuser can delete other user's note

    def test_search_annotations(self):
        search_url = reverse('annotation-api:search')
        notes = Annotation.objects.all()
        # user notes created by the test user
        user_notes = notes.filter(user__username=self.user_credentials['user']['username'])
        # search on partial text match
        resp = self.client.get(search_url, {'text': 'what a'})
        self.assertEqual('application/json', resp['Content-Type'])
        # check the data
        data = json.loads(resp.content.decode())
        self.assertEqual(0, data['total'],
            'anonymous user should not see any search results')

        # login as regular user
        self.client.login(**self.user_credentials['user'])
        resp = self.client.get(search_url, {'text': 'what a'})
        data = json.loads(resp.content.decode())

        if ANNOTATION_OBJECT_PERMISSIONS:
            # when per-object permissions are enabled, returned notes should
            # automatically be filtered by user
            self.assertEqual(user_notes.count(), data['total'])
            self.assertEqual(str(user_notes[0].id), data['rows'][0]['id'])

        else:
            # without per-object permissions, by default user can't view
            assert data['total'] == 0

            # add view permission and search again - should see all notes
            view_perm = Permission.objects.get(codename='view_annotation')
            testuser = get_user_model().objects.get(username='testuser')
            testuser.user_permissions.add(view_perm)
            resp = self.client.get(search_url, {'text': 'what a'})
            data = json.loads(resp.content.decode())
            assert data['total'] == notes.count()

        # login as superuser - should see all notes
        self.client.login(**self.user_credentials['superuser'])
        # matches both fixture notes
        resp = self.client.get(search_url, {'text': 'what a'})
        data = json.loads(resp.content.decode())
        self.assertEqual(notes.count(), data['total'])
        self.assertEqual(str(notes[0].id), data['rows'][0]['id'])
        self.assertEqual(str(notes[1].id), data['rows'][1]['id'])

        # search on uri
        resp = self.client.get(search_url, {'uri': notes[0].uri})
        data = json.loads(resp.content.decode())
        self.assertEqual(1, data['total'])
        self.assertEqual(notes[0].uri, data['rows'][0]['uri'])

        # search by username
        resp = self.client.get(search_url, {'user': self.user_credentials['user']['username']})
        data = json.loads(resp.content.decode())
        self.assertEqual(1, data['total'])
        self.assertEqual(str(user_notes[0].id), data['rows'][0]['id'])

        # limit/offset
        resp = self.client.get(search_url, {'limit': '1'})
        data = json.loads(resp.content.decode())
        self.assertEqual(1, data['total'])

        resp = self.client.get(search_url, {'offset': '1'})
        data = json.loads(resp.content.decode())
        self.assertEqual(notes.count() - 1, data['total'])
        # should return the *second* note first
        self.assertEqual(str(notes[1].id), data['rows'][0]['id'])

        # non-numeric pagination should be ignored
        resp = self.client.get(search_url, {'limit': 'three'})
        data = json.loads(resp.content.decode())
        self.assertEqual(notes.count(), data['total'])
