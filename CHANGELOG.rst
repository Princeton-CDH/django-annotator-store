.. _CHANGELOG:

CHANGELOG
=========

Release 0.7
-----------

* Django 2.0 compatible (`Ashwin Ramaswami <https://github.com/epicfaace>`
  `PR#6 <https://github.com/Princeton-CDH/django-annotator-store/pull/6>`_)
* Travis-CI build corrections and improvements (`Federico Bertani <https://github.com/federicoB>`_
  `PR#4 <https://github.com/Princeton-CDH/django-annotator-store/pull/4>`_,
  `PR#3 <https://github.com/Princeton-CDH/django-annotator-store/pull/3>`_)
* New `tox <http://tox.readthedocs.io/>`_ build to mirror Travis-CI
  build matrix of supported Python and Django versions with and without
  item-level permissions.

Release 0.6
-----------

* Creating new annotations via annotator API now requires the user
  to have the `annotator_store.add_annotation` permission.
  (Previously any logged in user could create annotations.)
* Any annotation edits (create, update, delete) made via annotator API
  now generate Django admin log entries.

Release 0.5
-----------

Initial release of `annotator_store` as a stand-alone django application,
refactored out of the `Readux <https://github.com/emory-libraries/readux>`_
codebase.

* Support for custom Annotation model via **ANNOTATOR_ANNOTATION_MODEL**
  setting and `annotator_store.models.BaseAnnotation` abstract model
* Configurable support for normal Django permissions *or* per-item
  permissions via **django-guardian** (*NOTE* that per-item permissions
  functionality is not fully tested or supported and should be
  considered alpha quality)
* Annotation text and quote fields marked as optional for use in Django admin
* Supports both Python 3.x and Python 2.7
* Includes example templates with code for initializing an annotator.js
  instance and connecting it to annotator_store as a backend.

