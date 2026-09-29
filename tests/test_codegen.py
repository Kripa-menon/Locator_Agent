from app.codegen import CodeGenerator


def test_codegen_with_frame():
    cg = CodeGenerator()
    best = {'type': 'css', 'value': '#login'}
    frame = {'id': 'frame-login', 'name': None, 'index': 0}
    snippets = cg.generate(best, frame)
    assert 'python' in snippets
    assert ('switch_to.frame' in snippets['python']) or ('switchTo().frame' in snippets['python'])
