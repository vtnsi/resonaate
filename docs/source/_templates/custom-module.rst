{{ fullname | escape | underline}}


.. automodule:: {{fullname}}
    :no-members:
    :noindex:

    {% block modules %}
    {% if modules or classes or functions or attributes or exceptions %}
    --------------------------
    {% endif %}
    {% if modules %}

    ..
        Summarize the sub-modules

    .. rubric:: {{ _('Submodules') }}

    .. autosummary::
        :toctree:
        :template: custom-module.rst
        :recursive:
    {% for item in modules %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% endblock %}


    {% block classes %}
    {% if classes %}
    ..
        Summarize the classes

    .. rubric:: {{ _('Classes') }}

    .. autosummary::
    {% for item in classes %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% endblock %}


    {% block functions %}
    {% if functions %}
    ..
        Summarize the functions

    .. rubric:: {{ _('Functions') }}

    .. autosummary::
        :nosignatures:
    {% for item in functions %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% endblock %}


    {% block attributes %}
    {% if attributes %}
    ..
        Summarize the attributes

    .. rubric:: {{ _('Module Attributes') }}

    .. autosummary::
    {% for item in attributes %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% endblock %}


    {% block exceptions %}
    {% if exceptions %}
    ..
        Summarize the exceptions

    .. rubric:: {{ _('Exceptions') }}

    .. autosummary::
    {% for item in exceptions %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% if modules or classes or functions or attributes or exceptions %}
    --------------------------
    {% endif %}
    {% endblock %}



.. rubric:: {{ _('Detailed Contents') }}


.. automodule:: {{fullname}}
    :members:
