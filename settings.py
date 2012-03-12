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

    def __init__(self, item_type=Unicode(), delimiter=':', **kwargs):
        self.item_type = item_type
        self.delimiter = delimiter
        super(KeyPair, self).__init__(parser=self.parser, **kwargs)


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
                        "Required item %r missing from section %r in ini file"\
                                % (iname, sname)
                    )
        return settings
