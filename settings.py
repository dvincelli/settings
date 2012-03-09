from ConfigParser import SafeConfigParser
import ast
import weakref


class Item(object):


    def __init__(self, parser=unicode, default=None, required=False):
        self.parser = parser
        self.default = default
        self.required = required
        self.registry = weakref.WeakKeyDictionary()

    def __set__(self, instance, value):
        value = self.parser(value)
        self.registry[instance] = value

    def __get__(self, instance, cls):
        return self.registry.get(instance, self.default)

    def __delete__(self, instance):
        del self.registry[instance]


class Boolean(Item):

    def boolean_parser(self, value):
        return value.lower() in ('true', 'yes', 'on', '1')

    def __init__(self, **kwargs):
        super(Boolean, self).__init__(
                parser=self.boolean_parser,
                **kwargs
            )


class Float(Item):

    def __init__(self, **kwargs):
        super(Float, self).__init__(
                parser=float,
                **kwargs
            )


class Integer(Item):

    def __init__(self, **kwargs):
        super(Integer, self).__init__(
                parser=int,
                **kwargs
            )


class Long(Item):

    def __init__(self, **kwargs):
        super(Long, self).__init__(
                parser=long,
                **kwargs
            )


class Unicode(Item):

    def __init__(self, **kwargs):
        super(Unicode, self).__init__(
                parser=unicode,
                **kwargs
            )


class KeyPair(Item):

    def parser(self, value):
        k, v = value.split(self.delimiter)
        v = self.item_type.parser(v)
        return (k, v)

    def __init__(self,
            item_type=Unicode(),
            delimiter=':',
            **kwargs
        ):
        self.item_type = item_type
        self.delimiter = delimiter
        super(KeyPair, self).__init__(
                parser=self.parser,
                **kwargs
            )


class List(Item):

    def __init__(self,
            item_type=Unicode(),
            seperator=',',
            multiline=False,
            strip=True,
            **kwargs
        ):
        self.item_type = item_type
        self.seperator = seperator
        self.multiline = multiline
        self.strip = strip
        super(List, self).__init__(
                parser=self.parser,
                **kwargs
            )

    def parser(self, value):
        if self.multiline:
            values = value.splitlines()
        else:
            values = value.split(self.seperator)

        if self.strip:
            values = [v.strip() for v in values]

        return [
            self.item_type.parser(v) for v in values
        ]

    def __get__(self, instance, value):
        return getattr(self, '_value', [])

    def __set__(self, instance, value):
        value = self.parser(value)
        setattr(self, '_value', value)


class PythonLiteral(Item):

    def __init__(self, **kwargs):
        super(PythonLiteral, self).__init__(
            parser=ast.literal_eval,
            **kwargs
        )


class DictAccessMixin(object):

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, item, value):
        return setattr(self, item, value)

    def __delitem__(self, item):
        return delattr(self, item)


class SectionMeta(type):

    def __new__(mcs, name, bases, dict):
        instance = type.__new__(mcs, name, bases, dict)
        items = {}
        for name, item in dict.iteritems():
            if isinstance(item, Item):
                items[name] = item
        instance.items = items
        return instance


class Section(DictAccessMixin):

    __metaclass__ = SectionMeta

    def get_required_items(self):
        for name, item in self.items.iteritems():
            if item.required:
                yield name, item


class Settings(DictAccessMixin):

    def __new__(cls, **kwargs):
        # just a little bit of magic to put proper instances
        # instead of classes on the resulting instance
        instance = super(Settings, cls).__new__(cls, **kwargs)
        for name, section in vars(cls).iteritems():
            try:
                if issubclass(section, Section):
                    setattr(instance, name, section())
            except TypeError:  # section is not a type
                pass
        return instance

    def add_section(self, name):
        setattr(self, name, Section())
        return getattr(self, name)

    def get_sections(self):
        for name, section in vars(self).iteritems():
            if isinstance(section, Section):
                yield name, section

    @classmethod
    def parse(cls, file):
        if isinstance(file, basestring):
            file = open(file)
        settings = cls()
        parser = SafeConfigParser()
        parser.readfp(file)
        # iterate over ini and set values
        for section in parser.sections():
            dest = getattr(settings, section, None)
            if dest is None:  # handle undelcared sections
                dest = settings.add_section(section)
            for (name, value) in parser.items(section):
                setattr(dest, name, value)
        for sname, section in settings.get_sections():
            for iname, item in section.get_required_items():
                if iname not in dict(parser.items(sname)):
                    raise ValueError(
                        "Required item %r missing from section %r in ini file" % (iname, sname)
                    )
        return settings



if __name__ == '__main__':

    class FunnelingSettings(Settings):

        class settings(Section):
            item1 = Unicode()
            item2 = Float()
            item3 = Integer(default=5)
            item4 = List(Unicode())
            item5 = List(KeyPair())

        class extra(Section):
            item = Integer()

    settings = FunnelingSettings()

    # unicode
    settings.settings.item1 = 4
    assert settings.settings.item1 == '4'

    # floats
    settings.settings.item2 = 45
    assert settings.settings.item2 == 45.0
    settings.settings.item2 = '41.0'
    assert settings.settings.item2 == 41.0

    # default
    assert settings.settings.item3 == 5
    settings.settings.item3 = '70'
    assert settings.settings.item3 == 70

    # two instances
    settings2 = FunnelingSettings()
    settings2.settings.item2 = 12
    assert settings2.settings.item2 == 12.0
    assert settings.settings.item2 == 41.0

    # lists
    settings2.settings.item4 = 'foo,bar,baz'
    assert settings2.settings.item4 == ['foo', 'bar', 'baz']

    # list of keypairs
    settings2.settings.item5 = 'foo:bar,baz:quux'
    assert settings2.settings.item5 == [('foo', 'bar'), ('baz', 'quux')]

    # dictionary access
    assert settings2['settings']['item5'] == settings2.settings.item5

    # whitespace fundamentals (WIP)
    setattr(settings2.settings, 'Miow Miow', 'Monkey Bot')
    assert settings2['settings']['Miow Miow'] == 'Monkey Bot'
    assert getattr(settings2['settings'], 'Miow Miow') == 'Monkey Bot'

    # exercise the parser function
    class MoreTests(Settings):

        class settings(Section):
            item1 = Unicode()
            integer = Integer()
            floatz = Float()
            lines = List(Float(), multiline=True)
            keypair_of_lists = KeyPair(List())
            some_dict_thing = PythonLiteral()
            a_long = Long()

        class extra(Section):
            pass

    from StringIO import StringIO
    foo = StringIO('''
[settings]
item1=foo
integer=-23423
floatz=423.2
lines=23.3
    32.3
    42
keypair_of_lists=k:x,y,z
some_dict_thing={'foo': 1, 2: [1, 2, 3]}
a_long=12345678901234567890

[extra]
What Up=dog

[undeclared]
what=huh?
''')
    settings = MoreTests.parse(foo)
    assert settings.settings.item1 == 'foo'
    assert settings.settings.integer == -23423
    assert settings.settings.floatz == 423.2
    assert settings.settings.lines == [23.3, 32.3, 42.0]
    # strange combo
    assert settings.settings.keypair_of_lists == ('k', ['x', 'y', 'z'])
    # python literral syntax
    assert settings.settings.some_dict_thing == {'foo': 1, 2: [1, 2, 3]}
    # python long
    assert settings.settings.a_long == 12345678901234567890L

    # trying out extra items that aren't defined
    assert settings.extra['what up'] == 'dog'

    # entirely undefined sections
    assert settings.undeclared.what == 'huh?'

    # required should blow up
    class Required(Settings):

        class settings(Section):
            required = Unicode(required=True)
            missing = Unicode()
            provided = Unicode()

    foo = StringIO('''
[settings]
provided = foo
''')
    try:
        settings = Required.parse(foo)
        assert False
    except ValueError as e:
        assert str(e) == "Required item 'required' missing from section 'settings' in ini file"

