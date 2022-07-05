Contribution Guide
==================

Contributions to this project, in all forms, are welcome. At this
point, we do not have formal governance or roles; the community that
we hope to form around this code will set them up as necessary. The
project is originally developed and shepherded by `Matific`_.

Community
---------

The project is run and managed on `Github`_. For issues or pull requests,
please use the tools provided there. For questions or support, please
reach out to project contributors:

+-------------+-----------------+---------------+-----------------------+
| Contributor | `Django Forum`_ | Github        | Other                 |
+=============+=================+===============+=======================+
| Shai Berger | shaib           | shaib         | Twitter: `@shaib_il`_ |
+-------------+-----------------+---------------+-----------------------+

In all communications and actions related to this project we ask that
you respect the code of conduct we blatantly copied from `Django`_ [*].

.. _Matific: https://www.matific.com/
.. _Github: https://github.com/Matific/broken-down-models
.. _`Django Forum`: https://forum.djangoproject.com
.. _`@shaib_il`: https://twitter.com/shaib_il/
.. _Django: https://www.djangoproject.com/conduct/

Code of Conduct
:::::::::::::::


- **Be friendly and patient.**
  
- **Be welcoming.** We strive to be a community that welcomes and
  supports people of all backgrounds and identities. This includes,
  but is not limited to members of any race, ethnicity, culture,
  national origin, colour, immigration status, social and economic
  class, educational level, sex, sexual orientation, gender identity
  and expression, age, size, family status, political belief,
  religion, and mental and physical ability.
  
- **Be considerate.** Your work will be used by other people, and you
  in turn will depend on the work of others. Any decision you take
  will affect users and colleagues, and you should take those
  consequences into account when making decisions. Remember that we're
  a world-wide community, so you might not be communicating in someone
  else's primary language.
    
- **Be respectful.** Not all of us will agree all the time, but
  disagreement is no excuse for poor behavior and poor manners. We
  might all experience some frustration now and then, but we cannot
  allow that frustration to turn into a personal attack. It's
  important to remember that a community where people feel
  uncomfortable or threatened is not a productive one. Members of our
  community should be respectful when dealing with other members as
  well as with people outside our community.
    
- **Be careful in the words that you choose.** We are a community of
  professionals, and we conduct ourselves professionally. Be kind to
  others. Do not insult or put down other participants. Harassment and
  other exclusionary behavior aren't acceptable. This includes, but is
  not limited to:
  
  - Violent threats or language directed against another person.

  - Discriminatory jokes and language.
    
  - Posting sexually explicit or violent material.
    
  - Posting (or threatening to post) other people's personally
    identifying information ("doxing").
    
  - Personal insults, especially those using racist or sexist terms.
    
  - Unwelcome sexual attention.
    
  - Advocating for, or encouraging, any of the above behavior.
    
  - Repeated harassment of others. In general, if someone asks you to stop, then stop.
    
- **When we disagree, try to understand why.** Disagreements, both
  social and technical, happen all the time and this project is no
  exception. It is important that we resolve disagreements and
  differing views constructively. Remember that we're different. The
  strength of the project comes from its varied community, people from
  a wide range of backgrounds. Different people have different
  perspectives on issues. Being unable to understand why someone holds
  a viewpoint doesn't mean that they're wrong. Don't forget that it is
  human to err and blaming each other doesn't get us anywhere.
  Instead, focus on helping to resolve issues and learning from
  mistakes.

Technically
-----------

The code and documentation for the project are included in the same
repository. Changes to code should be accompanied by respective changes
to tests and documentation, where relevant.

The project is tested against Python>=3.8 and supported versions of
Django (3.2.x, 4.0.x and the upcoming 4.1.x at the time this is written),
as well as Django's main branch. We
strongly recommend the latest stable point-release of each of the
above.

We use `poetry`_ to manage builds and `tox`_ to manage tests.

.. _poetry: https://python-poetry.org/
.. _tox: https://tox.readthedocs.io/en/latest/

If you want to dive into the code, we highly recommend reading the
:doc:`detailed explanations<./details>`.

Tests are collected in several groups:

- Tests which do not require database interaction are in the ``tests.py``
  module of the ``bdmodels`` package. These are mostly about the
  construction of fields and models.
  
- Tests which do require database interaction have been put into a test
  project, ``test_bdmodels``. These include:

  + Tests for querying, in ``testapp``. This is an app that defines the
    models to be used in tests, and the tests that use them.

  + A special module for profiling, ``testapp/test_profile.py``. See its
    docstring for details.

  + Tests for the migration operations, in an app called ``testmigs``.

  + Test apps brought over from Django's test suite, in order to
    validate further uses of relation fields with our Virtual relation
    fields; these require some adaptation, which is still a work in
    progress.

.. [*] After they stole it from the late `SpeakUp!`_ project
.. _`SpeakUp!`: http://web.archive.org/web/20141109123859/http://speakup.io/coc.html
