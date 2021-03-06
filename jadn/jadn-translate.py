"""
Translate JSON Abstract Data Notation (JADN) files to other formats.

Creates text-based representations of a JADN syntax, including
  * Prettyprinted JADN
  * JADN Source (JAS)
  * Markdown tables
  * Protobuf
  * Thrift

This script (jadn-translate) has no library dependencies other then jsonschema.

The jadn-convert script parses text representations into JADN, and creates representations that require
addtional libraries such as xlsxwriter.
"""

from __future__ import print_function
import os

from libs.codec import jadn_load, jadn_dump, jadn_analyze
from libs.convert import base_dump, jas_dump, proto_dump # , thrift_dump


if __name__ == "__main__":
    idir = 'schema'
    for fn in (f[0] for f in (os.path.splitext(i) for i in os.listdir(idir)) if f[1] == '.jadn'):
        print('**', fn)
        ifname = os.path.join(idir, fn)
        ofname = os.path.join("schema_gen", fn)

        # Prettyprint JADN, and convert to other formats

        source = ifname + ".jadn"
        dest = ofname + "_gen"
        schema = jadn_load(source)
        jadn_analyze(schema)
        jas_dump(schema, dest + ".jas", source)
        jadn_dump(schema, dest + ".jadn", source)
        base_dump(schema, dest + ".md", source, form='markdown')
        base_dump(schema, dest + ".html", source, form='html')
        proto_dump(schema, dest + ".proto3", source)
#       thrift_dump(schema, dest + ".thrift", source)
