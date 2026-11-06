import sys
from camel_tools.disambig.mle import MLEDisambiguator
from camel_tools.tokenizers.word import simple_word_tokenize

def print_header():
    print('Python version:', sys.version.split('\n')[0])
    try:
        import camel_tools
        print('camel-tools version:', camel_tools.__version__)
    except Exception as e:
        print('Failed to import camel_tools:', e)
        return

def test_words(words):
    disambig = MLEDisambiguator.pretrained()
    for w in words:
        analyses = disambig.analyze(w)
        if not analyses:
            print(f'Word "{w}": no analysis')
            continue
        # pick first (most probable) analysis
        best = analyses[0]
        print(f'Word "{w}": root={best.get("root")}, pos={best.get("pos")}, diac={best.get("diac")}, lex={best.get("lex")}')
        # show alternative roots
        alt_roots = set(a.get('root') for a in analyses)
        if len(alt_roots) > 1:
            print('  Alternative roots:', ', '.join(alt_roots))

def test_sentence(sentence):
    disambig = MLEDisambiguator.pretrained()
    tokens = simple_word_tokenize(sentence)
    print('Sentence tokens:', tokens)
    analyses = disambig.analyze_sentence(tokens)
    for token, analysis in zip(tokens, analyses):
        if analysis:
            print(f'"{token}": root={analysis.get("root")}, pos={analysis.get("pos")}, lex={analysis.get("lex")}')
        else:
            print(f'"{token}": no analysis')

if __name__ == '__main__':
    print_header()
    print('\n--- Individual word tests ---')
    test_words(['الوسواس', 'كتب', 'مكتبة', 'استخرج', 'آمنت'])
    print('\n--- Sentence context test ---')
    test_sentence('كتب الطالب الدرس')
    test_sentence('الطالب كتب الدرس')
