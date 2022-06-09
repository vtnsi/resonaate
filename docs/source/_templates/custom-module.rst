{{ fullname | escape | underline}}

.. automodule:: {{ fullname }}
    :members:

    {% if attributes or functions or classes or exceptions %}
    ----------------------
    {% endif %}

    {% block attributes %}
    {% if attributes %}
    .. rubric:: Module Attributes

    .. autosummary::
    {% for item in attributes %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% endblock %}

    {% block functions %}
    {% if functions %}
    .. rubric:: {{ _('Functions') }}

    .. autosummary::
    {% for item in functions %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% endblock %}

    {% block classes %}
    {% if classes %}
    .. rubric:: {{ _('Classes') }}

    .. autosummary::
    {% for item in classes %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% endblock %}

    {% block exceptions %}
    {% if exceptions %}
    .. rubric:: {{ _('Exceptions') }}

    .. autosummary::
    {% for item in exceptions %}
        {{ item }}
    {%- endfor %}
    {% endif %}
    {% endblock %}

    {% if attributes or functions or classes or exceptions %}
    ------------------------
    {% endif %}

{% block modules %}
{% if modules %}

--------------------------

.. rubric:: Submodules

.. autosummary::
    :toctree:
    :template: custom-module.rst
    :recursive:
{% for item in modules %}
    {{ item }}
{%- endfor %}
{% endif %}
{% endblock %}
