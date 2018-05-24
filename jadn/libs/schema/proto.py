import json
import re

from ..utils import Utils


class JADNtoProto3(object):
    def __init__(self, jadn):
        """
        Schema Converter for JADN to ProtoBuf3
        :param jadn: str or dict of the JADN schema
        :type jadn: str
        """
        if type(jadn) is str:
            try:
                jadn = json.loads(jadn)
            except Exception as e:
                raise e

            self._meta = jadn['meta'] or None
            self._types = jadn['types'] or None

        elif type(jadn) is dict:
            self._meta = jadn['meta'] or None
            self._types = jadn['types'] or None

        else:
            raise TypeError('JADN improperly formatted')

        self._imports = []
        self.indent = '  '

        self._customFields = Utils.defaultDecode([t for t in self._types if len(t) == 4])
        self._fieldsCustom = {t[0]: t[1] for t in self._customFields}
        self._fieldTypes = [t[0] for t in self._types if len(t) == 5]
        self._fieldMap = {
            'Binary': 'string',
            'Boolean': 'bool',
            'Integer': 'int64',
            'Number': 'string',
            'Null': 'string',
            'String': 'string'
        }
        self._structFormats = {
            'Record': self._formatRecord,
            'Choice': self._formatChoice,
            'Map': self._formatMap,
            'Enumerated': self._formatEnumerated,
            'Array': self._formatArray,
            'ArrayOf': self._formatArrayOf,
        }

    def proto_dump(self):
        """
        Converts the JADN schema to Protobuf3
        :return: Protobuf3 schema
        :rtype str
        """
        return '{header}{imports}{defs}\n/* JADN Custom Fields\n[\n{jadn_fields}\n]\n*/'.format(
            idn=self.indent,
            header=self.makeHeader(),
            defs=self.makeStructures(),
            imports=''.join(['import \"{}\";\n'.format(i) for i in self._imports]),
            jadn_fields=',\n'.join([self.indent+f.__str__() for f in self._customFields])
        )

    def formatStr(self, s):
        """
        Formats the string for use in schema
        :param s: string to format
        :type s: str
        :return: formatted string
        :rtype str
        """
        if s == '*':
            return 'unknown'
        else:
            return re.sub(r'[\- ]', '_', s)

    def makeHeader(self):
        """
        Create the header for the schema
        :return: header for schema
        :rtype str
        """
        header = list([
            'syntax = "proto3";',
            '',
            'package {};'.format(self._meta['module'] or 'ProtoBuf_Schema'),
            '',
            '/* meta'
        ])

        header.extend([' * {} - {}'.format(k, v) for k, v in self._meta.items()])

        header.append('*/')

        return '\n'.join(header) + '\n\n'

    def makeStructures(self):
        """
        Create the type definitions for the schema
        :return: type definitions for the schema
        :rtype str
        """
        tmp = ''
        for t in self._types:
            if len(t) == 5:
                # print('type - {}'.format(t[:-1]))
                df = self._structFormats.get(t[1], None)

                if df is not None and t[1] in ['Record', 'Enumerated', 'Map']:
                    tmp += df(t)
                elif df is not None:
                    tmp += self._wrapAsRecord(df(t))

        return tmp

    def _wrapAsRecord(self, itm):
        """
        wraps the given item as a record for the schema
        :param itm: item to wrap
        :type s: str
        :return: item wrapped as a record for hte schema
        :rtype str
        """
        lines = itm.split('\n')[1:-1]
        if len(lines) > 1:
            n = re.search(r'\s[\w\d\_]+\s', lines[0]).group()[1:-1]
            tmp = "\nmessage {} {{\n".format(self.formatStr(n))
            for l in lines:
                tmp += '{}{}\n'.format(self.indent, l)
            tmp += '}\n'
            return tmp
        return ''

    def _fieldType(self, f):
        """
        Determines the field type for the schema
        :param f: current type
        :return: type mapped to the schema
        :rtype str
        """
        if re.search(r'(datetime|date|time)', f):
            if 'google/protobuf/timestamp.proto' not in self._imports:
                self._imports.append('google/protobuf/timestamp.proto')
            return 'google.protobuf.Timestamp'
        elif f not in self._fieldTypes:
            return 'string'
        # print(f)
        return self.formatStr(self._fieldMap.get(self._fieldsCustom.get(f, f), f))

    # Structure Formats
    def _formatRecord(self, itm):
        """
        Formats records for the given schema type
        :param itm: record to format
        :return: formatted record
        :rtype str
        """
        tmp = "\nmessage {} {{".format(self.formatStr(itm[0]))
        opts = {'type': itm[1]}
        if len(itm[2]) > 0: opts['options'] = itm[2]
        tmp += ' // {}#jadn_opts:{}\n'.format('' if itm[-2] == '' else itm[-2]+' ', json.dumps(opts))

        for l in itm[-1]:
            tmp += '{}{} {} = {};'.format(self.indent, self._fieldType(l[2]), self.formatStr(l[1]), l[0])
            opts = {'type': l[2]}
            if len(l[-2]) > 0: opts['options'] = l[-2]
            tmp += ' // {}#jadn_opts:{}\n'.format('' if l[-1] == '' else l[-1]+' ', json.dumps(opts))
        tmp += "}\n"

        return tmp

    def _formatChoice(self, itm):
        """
        Formats choice for the given schema type
        :param itm: choice to format
        :return: formatted choice
        :rtype str
        """
        tmp = '\n'
        tmp += "oneof {} {{".format(self.formatStr(itm[0]))
        opts = {'type': itm[1]}
        if len(itm[2]) > 0: opts['options'] = itm[2]
        tmp += ' // {}#jadn_opts:{}\n'.format('' if itm[-2] == '' else itm[-2]+' ', json.dumps(opts))

        for l in itm[-1]:
            tmp += '{}{} {} = {};'.format(self.indent, self._fieldType(l[2]), self.formatStr(l[1]), l[0])
            opts = {'type': l[2]}
            if len(l[-2]) > 0: opts['options'] = l[-2]
            tmp += ' // {}#jadn_opts:{}\n'.format('' if l[-1] == '' else l[-1]+' ', json.dumps(opts))
        tmp += '}\n'
        return tmp

    def _formatMap(self, itm):
        """
        Formats map for the given schema type
        :param itm: map to format
        :return: formatted map
        :rtype str
        """
        return self._formatRecord(itm)

    def _formatEnumerated(self, itm):
        """
        Formats enum for the given schema type
        :param itm: enum to format
        :return: formatted enum
        :rtype str
        """
        tmp = '\nenum {} {{'.format(self.formatStr(itm[0]))
        opts = {'type': itm[1]}
        if len(itm[2]) > 0: opts['options'] = itm[2]
        tmp += ' // {}#jadn_opts:{}\n'.format('' if itm[-2] == '' else itm[-2]+' ', json.dumps(opts))

        lines = []
        default = True
        for l in itm[-1]:
            if l[0] == 0:
                default = False
            n = self.formatStr(l[1] or 'Unknown_{}_{}'.format(self.formatStr(itm[0]), l[0]))
            ltmp = '{}{} = {};'.format(self.indent, n, l[0])
            ltmp += '\n' if l[-1] == '' else ' // {}\n'.format(l[-1])
            lines.append(ltmp)

        if default:
            tmp += '{}Unknown_{} = 0; // required starting enum number for protobuf3\n'.format(self.indent, itm[0].replace('-', '_'))
        tmp += ''.join(lines)

        tmp += "}\n"
        return tmp

    def _formatArray(self, itm):
        """
        Formats array for the given schema type
        :param itm: array to format
        :return: formatted array
        :rtype str
        """
        return ''

    def _formatArrayOf(self, itm):
        """
        Formats arrayof for the given schema type
        :param itm: arrayof to format
        :return: formatted arrayof
        :rtype str
        """
        return ''


class Proto3toJADN(object):
    def __init__(self, proto):
        """
        Schema Converter for ProtoBuf3 to JADN
        :param proto: str or dict of the JADN schema
        :type proto: str
        """
        self._proto = proto
        self.indent = '  '

        self._fieldMap = {
            'enum': 'Enumerated',
            'message': 'Record',
            'oneof': 'Choice',
            # primitives
            'string': 'String'
        }
        self._structs = [
            'Record',
            'Choice',
            'Map',
            'Enumerated',
            'Array',
            'ArrayOf'
        ]

        self._fieldRegex = {
            'enum': re.compile(r'(?P<name>.*?)\s+=\s+(?P<id>\d+);(\s+//\s+(?P<comment>.*))?\n?'),
            'message': re.compile(r'(?P<type>.*?)\s+(?P<name>.*?)\s+=\s+(?P<id>\d+);(\s+//\s+(?P<comment>.*))?\n?')
        }
        self._fieldRegex['oneof'] = self._fieldRegex['message']

    def jadn_dump(self):
        """
        Converts the Protobuf3 schema to JADN
        :return: JADN schema
        :rtype str
        """
        meta = "{idn}\"meta\": {{\n{meta}\n{idn}}}".format(
            idn=self.indent,
            meta=',\n'.join(["{idn}{idn}\"{mk}\": \"{mv}\"".format(idn=self.indent, mk=k, mv=v) for k, v in self.makeHeader().items()])
        )

        types = "[\n{obj},\n{custom}\n{idn}]".format(
            idn=self.indent,
            obj=',\n'.join([
                self._formatType(t) for t in self.makeTypes()
            ]),
            custom=',\n'.join([
                '{idn}{idn}{field}'.format(idn=self.indent, field=f.__str__().replace('\'', '\"')) for f in self.makeCustom()
            ])
        )

        return "{{\n{meta},\n{idn}\"types\": {types}\n}}".format(
            idn=self.indent,
            meta=meta,
            types=types
        )

    def formatStr(self, s):
        """
        Formats the string for use in schema
        :param s: string to format
        :type s: str
        :return: formatted string
        :rtype str
        """
        if s == '*':
            return 'unknown'
        else:
            return re.sub(r'[\- ]', '_', s)

    def makeHeader(self):
        """
        Create the header for the schema
        :return: header for schema
        :rtype dict
        """
        tmp = {}
        meta = re.search(r'/\* meta[\n\w\d\-*. ]+\*/', self._proto)
        if meta:
            for meta_line in meta.group().split('\n')[1:-1]:
                line = re.sub(r'^\s+\*\s+', '', meta_line).split(' - ')
                tmp[line[0]] = ' - '.join(line[1:])

        return tmp

    def makeTypes(self):
        """
        Create the type definitions for the schema
        :return: type definitions for the schema
        :rtype list
        """
        tmp = []
        for type_def in re.findall(r'^((enum|message)(.|\n)*?^\}$)', self._proto, flags=re.MULTILINE):
            tmp_type = []
            def_lines = type_def[0].split('\n')
            if re.match(r'^\s+(oneof)', def_lines[1]):
                def_lines = def_lines[1:-1]

            proto_type, field_name = def_lines[0].split(r'{')[0].split()

            c = def_lines[0].split('//')
            c = (c[1][1:] if c[1].startswith(' ') else c[1]) if len(c) > 1 else ''
            opts, c = self._loadOpts(c)

            jadn_type = self._fieldMap.get(proto_type, 'Record')
            jadn_type = jadn_type if jadn_type == opts.get('type', jadn_type) else opts['type']

            tmp_type.extend([
                field_name,
                jadn_type,
                opts.get('options', []),  # options ??
                c
            ])

            tmp_defs = []
            for def_var in def_lines[1:-1]:
                def_var = re.sub(r'^\s+', '', def_var)
                parts = self._fieldRegex.get(proto_type, self._fieldRegex['message']).match(def_var)

                if parts:
                    parts = parts.groupdict()
                    opts, parts['comment'] = self._loadOpts(parts['comment'])

                    if proto_type == 'enum':
                        if parts['name'] == 'Unknown_{}'.format(field_name): continue

                        # id, name, comment
                        tmp_defs.append([
                            int(parts['id']) if parts['id'].isdigit() else parts['id'],
                            parts['name'],
                            parts['comment'] or ''
                        ])

                    elif proto_type in ['message', 'oneof']:
                        field_type = self._fieldType(parts['type'])
                        field_type = field_type if field_type == opts.get('type', field_type) else opts['type']

                        # id, name, type, opts, comment
                        tmp_defs.append([
                            int(parts['id']) if parts['id'].isdigit() else parts['id'],
                            parts['name'],
                            field_type,
                            opts.get('options', []),
                            parts['comment'] or ''
                        ])

                    else:
                        # tmp_defs.append([])
                        pass
                else:
                    print('{} - {}'.format(proto_type, def_var))
                    print('Something Happened....')

            tmp_type.append(tmp_defs)
            tmp.append(tmp_type)
        return tmp

    def makeCustom(self):
        customFields = re.search(r'/\* JADN Custom Fields\n(?P<custom>[\w\W]+?)\n\*/', self._proto)

        if customFields:
            try:
                fields = Utils.defaultDecode(json.loads(customFields.group('custom').replace('\'', '\"')))
            except Exception as e:
                fields = []
                print('oops....')

        return fields

    def _formatType(self, t):
        tmp = ','.join(['\n{idn}{idn}{idn}{defn}'.format(idn=self.indent, defn=td.__str__()) for td in t[-1]])

        if tmp != '':
            tmp += '\n{idn}{idn}'.format(idn=self.indent)

        return '{idn}{idn}{head}, [{defs}]]'.format(
            idn=self.indent,
            head=t[:-1].__str__()[:-1],
            defs=tmp
        ).replace('\'', '\"')

    def _fieldType(self, f):
        if re.match(r'^google', f):
            ft = 'String'
        else:
            ft = self._fieldMap.get(f, f)

        return ft

    def _loadOpts(self, com):
        c = com or ''
        comment = re.sub(r'\s?#jadn_opts:(?P<opts>{.*?})\n?', '', c)
        if c == comment:
            return {}, comment

        opts = re.match(r'\s*?#jadn_opts:(?P<opts>{.*?})\n?', c.replace(comment, ''))
        if opts:
            try:
                opts = json.loads(opts.group('opts'))
                opts['type'] = str(opts['type'])
                if 'options' in opts: opts['options'] = [str(o) for o in opts['options']]
            except Exception:
                print('oops...')
                opts = {}
        else:
            opts = {}

        return opts, comment