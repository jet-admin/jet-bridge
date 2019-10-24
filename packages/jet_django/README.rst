===================
Jet Bridge (Django)
===================

**Universal admin panel for Django**

.. image:: https://s3.us-west-2.amazonaws.com/secure.notion-static.com/079701bd-ea68-4848-a885-d19518cfa746/main.gif?AWSAccessKeyId=AKIAJLJXUMP5IHUZAPFQ&Expires=1539710956&Signature=zSY1L770Uu0gCtG72%2FAGE8rm9G0%3D
    :alt: Preview
    :align: center
    :target: https://s3.us-west-2.amazonaws.com/secure.notion-static.com/079701bd-ea68-4848-a885-d19518cfa746/main.gif?AWSAccessKeyId=AKIAJLJXUMP5IHUZAPFQ&Expires=1539710956&Signature=zSY1L770Uu0gCtG72%2FAGE8rm9G0%3D

Description
===========

* Jet Admin: https://about.jetadmin.io
* **Live Demo**: http://app.jetadmin.io/demo
* Support: support@jetadmin.io

**Jet** is a SaaS service that automatically generates back office for your Django Application through REST API of **Jet Bridge** package installed to your project.

– **Visual**. Admin interface can be easily changed without need of development with the help of Visual Editor. 

– **Secure**. Jet does not access your data: its transferred directly from browser to your application.

– **Customizable**. Flex functions allow you to solve your specific business tasks when standard functionality is not enough.

This is a complete remake of popular `Django Jet <https://github.com/geex-arts/django-jet>`_ admin interface.

Features
========

- **CRUD (create, read, update, delete):**
  
  Create, view, update and delete data. Display it in an easy format, and then search and filter your data.

- **Dashboard:** 

  Create reports and visualize KPIs. Monitor new data like new orders, comments, etc.
  
- **Works with any technology:** 

  The interface is generated automatically based on an analysis of the data and data structure of your applications.

- **Visual editor:** 
  
  Customize the admin area to make it easy for any manager to use. Allow managers to modify the interface, configure features, and set up analytics widgets without using any developers — just like WIX, Squarespace….

- **Secure:** 

  Your data is safe. We do not have access to your information. We simply plug your information in to an easy-to-use interface for you to interact with it better.

- **Works on any device:** 

  The interface is optimized for any device from phones to tablets to desktops.

- **Quick installation:** 

  It takes only a few hours to integrate with your project.

- **Available 24/7:** 

  Use it around the clock and don’t worry about updates — we take care of that.

- **Manage users:** 

  Assign access rights to any data from within the panel.

- **Activity log:** 

  Track the history of all changes and know who made them.

Requirements
============

- **Python** – 3.4, 3.5, 3.6, 3.7
- **Django** – 1.11, 2.0, 2.1

Installation
============


**1. Download and install latest version of Jet Bridge:**

.. code-block:: python

  pip install jet-django


**2. Add 'jet_django' application to the INSTALLED_APPS setting of your Django project settings.py file:**

.. code-block:: python
  
  INSTALLED_APPS = (
    ...
    'jet_django',
    ...
  )

**3. Add URL-pattern to the urlpatterns of your Django project urls.py file:**

.. code-block:: python

  from jet_django.urls import jet_urls
  
  urlpatterns = [
    ...
    url(r'^jet_api/', include(jet_urls)),
    ...
  ]

**4. Apply migrations:**

.. code-block:: python
  
  python manage.py migrate jet_django

**5. Restart your project**

**6. Open https://YOUR_PROJECT_URL/jet_api/register/ in browser to create a project**

Support
=======

Feel free to Email us – support@jetadmin.io

License
=======

This project is **MIT** licensed - see the LICENCE file for details.
