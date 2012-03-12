import unittest
import settings
from settings import (
        Float,
        Integer,
        KeyPair,
        List,
        Long,
        PythonLiteral,
        Section,
        Settings,
        Unicode
    )
from StringIO import StringIO


class SomeSettings(Settings):

    class settings(Section):
        item1 = Unicode()
        item2 = Float()
        item3 = Integer(default=5)
        item4 = List(Unicode())
        item5 = List(KeyPair())
        int = Integer()
        long = Long()

    class extra(Section):
        item = Integer()


class MoreSettings(Settings):

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


class SettingsTests(unittest.TestCase):

    def setUp(self):
        self.conf1 = SomeSettings()
        self.conf2 = MoreSettings()
        self.conf2 = self.conf2.parse(StringIO('''
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
'''))

    def test_Unicode_casts_to_unicode(self):
        self.conf1.settings.item1 = 4
        self.assertEquals(u'4', self.conf1.settings.item1)
        self.assertEquals(unicode, type(self.conf1.settings.item1))

    def test_Float_casts_to_float(self):
        self.conf1.settings.item2 = 45
        self.assertEquals(45.0, self.conf1.settings.item2)
        self.assertEquals(float, type(self.conf1.settings.item2))

        self.conf1.settings.item2 = '41.0'
        self.assertEquals(41.0, self.conf1.settings.item2)
        self.assertEquals(float, type(self.conf1.settings.item2))

    def test_Integer_casts_to_int(self):
        self.conf1.settings.int = '10'
        self.assertTrue(10 is self.conf1.settings.int)
        self.assertEquals(int, type(self.conf1.settings.int))

    def test_Long_casts_to_long(self):
        self.conf1.settings.long = '100L'
        self.assertEquals(type(100L), type(self.conf1.settings.long))
        self.assertEquals(100L, self.conf1.settings.long)

    def test_default(self):
        self.assertEquals(5, self.conf1.settings.item3)

    def test_default_is_overriden(self):
        self.conf1.settings.item3 = '70'
        self.assertEquals(70, self.conf1.settings.item3)

    def test_two_instances_no_shared_state(self):
        conf3 = SomeSettings()
        self.conf1.settings.item2 = '41'
        conf3.settings.item2 = 12
        self.assertEquals(12.0, conf3.settings.item2)
        self.assertEquals(41.0, self.conf1.settings.item2)

    def test_list_parsing(self):
        self.conf1.settings.item4 = 'foo,bar,baz'
        assert self.conf1.settings.item4 == ['foo', 'bar', 'baz']

    def test_list_of_keypairs(self):
        self.conf1.settings.item5 = 'foo:bar,baz:quux'
        self.assertEquals(
                [('foo', 'bar'), ('baz', 'quux')],
                self.conf1.settings.item5
            )

    def test_dictionary_access(self):
        self.conf1.settings.item5 = 'foo:bar,baz:quux'
        self.assertEquals(
                [('foo', 'bar'), ('baz', 'quux')],
                self.conf1['settings']['item5']
            )

    def test_whitespace_attributes(self):
        setattr(self.conf2.settings, 'Miow Miow', 'Monkey Bot')
        self.assertEquals('Monkey Bot', self.conf2['settings']['Miow Miow'])
        self.assertEquals('Monkey Bot', getattr(self.conf2['settings'], 'Miow Miow'))

    def test_parser(self):
        self.assertEquals('foo', self.conf2.settings.item1)
        self.assertEquals(-23423, self.conf2.settings.integer)
        self.assertEquals(423.2, self.conf2.settings.floatz)
        self.assertEquals([23.3, 32.3, 42.0], self.conf2.settings.lines)
        # strange combo
        self.assertEquals(('k', ['x', 'y', 'z']), self.conf2.settings.keypair_of_lists)
        # python literral syntax
        self.assertEquals({'foo': 1, 2: [1, 2, 3]}, self.conf2.settings.some_dict_thing)
        # python long
        self.assertEquals(12345678901234567890L, self.conf2.settings.a_long)

        # trying out extra items that aren't defined
        self.assertEquals('dog', self.conf2.extra['what up'])

        # entirely undefined sections
        self.assertEquals('huh?', self.conf2.undeclared.what)

    def test_missing_required_items_raise(self):
        class Required(Settings):

            class settings(Section):
                required = Unicode(required=True)
                missing = Unicode()
                provided = Unicode()

        ini = StringIO('''
[settings]
provided = foo
        ''')

        self.assertRaises(ValueError, Required.parse, ini)
