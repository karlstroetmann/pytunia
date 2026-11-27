// The grammar of Jasmin assembly files, written for the parser generator Larkita
// (https://github.com/karlstroetmann/Larkita).  It describes the same language as the
// grammar of Jasmin 2.4 (src/jasmin/parser.cup).
//
// The tokens come from pytunia's scanner (scanner.py), not from Larkita's lexer, so the
// grammar defines no terminals.  Every string literal is a reserved word of Jasmin; the
// scanner never returns a reserved word as a WORD.  The other tokens are
//
//     EOL       the end of a line: one or more line breaks and comments.  Its value is
//               the number of the line where the statement that it ends started.
//     WORD      a name, e.g. java/lang/Object or main([Ljava/lang/String;)V
//     INSN      the name of a JVM instruction, e.g. iload
//     STR       a string in double quotes; the value has its escape sequences resolved
//     INT       an integer that fits into 32 bits (a Python int)
//     NUM       any other number (a JavaLong, JavaFloat or JavaDouble)
//     RELATIVE  a relative branch target such as $+5 (a Python int)
//
// translator.py walks the abstract syntax trees that Larkita builds from this grammar.

%declare EOL WORD INSN STR INT NUM RELATIVE;

jas_file: header inner_spec* field_spec* method_spec*;

// ----------------------------------------------------------------------------
// the class header
// ----------------------------------------------------------------------------

header: [bytecode_spec] [source_spec] class_spec super_spec implements_spec*
        [signature_spec] [enclosing_spec] [deprecated_spec] annotation*
        attribute_spec* debug_spec*;

bytecode_spec:   ".bytecode" NUM EOL;
source_spec:     ".source" (STR | WORD) EOL;
class_spec:      (".class" | ".interface") access WORD EOL;
super_spec:      ".super" WORD EOL;
implements_spec: ".implements" WORD EOL;
signature_spec:  ".signature" STR EOL;
enclosing_spec:  ".enclosing" "method" WORD EOL  -> ".enclosing";
deprecated_spec: ".deprecated" EOL;
attribute_spec:  ".attribute" WORD STR EOL;
debug_spec:      ".debug" STR EOL;

// the access flags, e.g. ("access", "public", "static")
access: ("public" | "private" | "protected" | "static" | "final" | "synchronized"
        | "volatile" | "transient" | "native" | "interface" | "abstract"
        | "annotation" | "enum" | "bridge" | "varargs" | "fpstrict" | "synthetic")*;

// ----------------------------------------------------------------------------
// inner classes
// ----------------------------------------------------------------------------

// .inner class|interface <access> [<name>] [inner <class>] [outer <class>]
inner_spec: ".inner" ("class" | "interface") access inner_name inner_class outer_class EOL
            -> ".inner";
inner_name:  [WORD];
inner_class: ["inner" WORD];
outer_class: ["outer" WORD];

// ----------------------------------------------------------------------------
// fields
// ----------------------------------------------------------------------------

// a field on one line, or a field with attributes that ends with .end field
field_spec: ".field" access WORD WORD field_signature field_value EOL
          | ".field" access WORD WORD field_value EOL
          | ".field" field_start field_attribute* ".end" "field" EOL  -> ".field block";

field_signature: "signature" STR;
field_value:     ["=" item];
field_start:     access WORD WORD field_value EOL;

field_attribute: ".signature" STR EOL
               | ".attribute" WORD STR EOL
               | ".deprecated" EOL
               | annotation
               ;

// ----------------------------------------------------------------------------
// annotations
// ----------------------------------------------------------------------------

// an annotation of a class or a field
annotation: ".annotation" ("visible" | "invisible") WORD EOL annotation_field*
            ".end" "annotation" EOL  -> ".annotation";

// an annotation of a method or of one of its parameters, or the default value of an
// annotation element; they are statements, so they are followed by an EOL
method_annotation:
      ".annotation" ("visible" | "invisible") WORD EOL annotation_field*
      ".end" "annotation"  -> ".annotation"
    | ".annotation" ("visibleparam" | "invisibleparam") INT WORD EOL annotation_field*
      ".end" "annotation"  -> ".annotation param"
    | ".annotation" "default" EOL WORD [WORD] "=" annotation_values
      ".end" "annotation"  -> ".annotation default"
    ;

// <name> <descriptor> [<type>] = <values>
annotation_field: WORD WORD [WORD] "=" annotation_values;

// either values on one line, or nested annotations
annotation_values: any_item+ EOL
                 | nested_annotation+
                 ;

nested_annotation: ".annotation" EOL annotation_field* ".end" "annotation" EOL
                   -> "nested annotation";

item:     INT | NUM | STR;
any_item: WORD | item;

// ----------------------------------------------------------------------------
// methods
// ----------------------------------------------------------------------------

method_spec: ".method" access WORD EOL statement* ".end" "method" EOL  -> ".method";

statement: [instruction | directive | label] EOL;

label: WORD ":"
     | INT ":" instruction
     ;

// ----------------------------------------------------------------------------
// instructions
// ----------------------------------------------------------------------------

instruction: INSN [INT | INT INT | NUM | WORD | WORD INT | WORD WORD | STR | RELATIVE]
           | lookupswitch
           | tableswitch
           ;

// lookupswitch
//     <key> : <label or offset>
//     ...
//     default : <label or offset>
lookupswitch: "lookupswitch" EOL lookup_entry+ "default" ":" (WORD | INT)
              -> "lookupswitch";
lookup_entry: INT ":" (WORD | INT) EOL;

// tableswitch <low> [<high>]
//     <label or offset>
//     ...
//     default : <label or offset>
tableswitch: "tableswitch" INT [INT] EOL table_entry+ "default" ":" (WORD | INT)
             -> "tableswitch";
table_entry: (WORD | INT) EOL;

// ----------------------------------------------------------------------------
// directives in methods
// ----------------------------------------------------------------------------

directive: ".var" INT "is" WORD WORD var_signature                        -> ".var"
         | ".var" INT "is" WORD WORD var_signature "from" WORD "to" WORD  -> ".var"
         | ".var" INT "is" WORD WORD var_signature "from" INT "to" INT    -> ".var"
         | ".limit" ("locals" | "stack") INT
         | ".limit" WORD INT
         | ".line" INT
         | ".throws" WORD
         | ".catch" WORD "from" WORD "to" WORD "using" WORD  -> ".catch"
         | ".catch" WORD "from" INT "to" INT "using" INT     -> ".catch"
         | ".set" WORD any_item
         | ".signature" STR
         | ".attribute" WORD STR
         | ".deprecated"
         | method_annotation
         | stack_map
         ;

var_signature: ["signature" STR];

// .stack                       .stack use [<n>] locals
//     [offset <label or offset>]
//     locals <type> [<value>]
//     stack <type> [<value>]
// .end stack
stack_map: ".stack" EOL stack_offset stack_item* ".end" "stack"  -> ".stack"
         | ".stack" "use" [INT] "locals" EOL stack_offset stack_item* ".end" "stack"
           -> ".stack use";

stack_offset: ["offset" (INT | WORD) EOL];
stack_item:   ("locals" | "stack") WORD [WORD | INT] EOL;
