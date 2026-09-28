class CodeGenerator:
    def __init__(self):
        pass

    def generate(self, best_locator: dict, frame=None):
        # return simplified code snippets dict for languages
        if not best_locator:
            return {}
        typ = best_locator.get('type')
        val = best_locator.get('value')
        snippets = {}

        # Python
        if typ == 'css':
            sel = f"(By.CSS_SELECTOR, \"{val}\")"
        else:
            sel = f"(By.XPATH, \"{val}\")"
        py = f"WebDriverWait(driver, 10).until(EC.element_to_be_clickable({sel})).click()"
        snippets['python'] = py

        # Java
        java = f"new WebDriverWait(driver, 10).until(ExpectedConditions.elementToBeClickable({ 'By.cssSelector(\"'+val+'\")' if typ=='css' else 'By.xpath(\"'+val+'\")' })).click();"
        snippets['java'] = java

        # JavaScript
        js = f"const el = await driver.wait(until.elementLocated(By.{ 'css' if typ=='css' else 'xpath' }('{val}')), 10000);\nawait el.click();"
        snippets['javascript'] = js

        # TypeScript (typed)
        ts = f"const el: WebElement = await driver.wait(until.elementLocated(By.{ 'css' if typ=='css' else 'xpath' }('{val}')), 10000);\nawait el.click();"
        snippets['typescript'] = ts

        # C#
        cs = f"new WebDriverWait(driver, TimeSpan.FromSeconds(10)).Until(ExpectedConditions.ElementToBeClickable({ 'By.CssSelector("'+val+'")' if typ=='css' else 'By.XPath("'+val+'")' })).Click();"
        snippets['csharp'] = cs

        # If frame info provided, prepend full frame-switch code per language
        if frame:
            fid = frame.get('id') or frame.get('name')
            idx = frame.get('index')
            new = {}
            for lang, body in snippets.items():
                prefix = ''
                if lang == 'python':
                    if fid:
                        prefix = f"# switch to frame by name/id '{fid}'\niframe = driver.find_element(By.ID, '{fid}') if driver.find_elements(By.ID, '{fid}') else driver.find_element(By.NAME, '{fid}')\ndriver.switch_to.frame(iframe)\n"
                    elif idx is not None:
                        prefix = f"# switch to frame index {idx}\ndriver.switch_to.frame({idx})\n"
                elif lang == 'java':
                    if fid:
                        prefix = f"// switch to frame by name/id '{fid}'\nWebElement iframe = driver.findElements(By.id(\"{fid}\")).size()>0 ? driver.findElement(By.id(\"{fid}\")) : driver.findElement(By.name(\"{fid}\"));\ndriver.switchTo().frame(iframe);\n"
                    elif idx is not None:
                        prefix = f"// switch to frame index {idx}\ndriver.switchTo().frame({idx});\n"
                elif lang == 'javascript' or lang == 'typescript':
                    if fid:
                        prefix = f"// switch to frame by name/id '{fid}'\nconst frames = await driver.findElements(By.css('iframe[name=\"{fid}\"], iframe#{fid}'));\nif(frames.length>0) await driver.switchTo().frame(frames[0]);\n"
                    elif idx is not None:
                        prefix = f"// switch to frame index {idx}\nawait driver.switchTo().frame({idx});\n"
                elif lang == 'csharp':
                    if fid:
                        prefix = f"// switch to frame by name/id '{fid}'\nvar ifr = driver.FindElements(By.Id(\"{fid}\")).Count>0 ? driver.FindElement(By.Id(\"{fid}\")) : driver.FindElement(By.Name(\"{fid}\"));\ndriver.SwitchTo().Frame(ifr);\n"
                    elif idx is not None:
                        prefix = f"// switch to frame index {idx}\ndriver.SwitchTo().Frame({idx});\n"
                new[lang] = prefix + body
            snippets = new
        # If detected shadow DOM requirement, also add JS snippets to pierce shadow roots
        # We'll add a JS helper that queries through shadow roots. For other languages, include a JS snippet note.
        def wrap_shadow(js_body):
            helper = """
const queryShadow = (selectors) => {
  const parts = selectors.split('>>>');
  let node = document;
  for(const p of parts){
    if(!node) return null;
    const sel = p.trim();
    if(node instanceof Document){ node = node.querySelector(sel); }
    else if(node.shadowRoot){ node = node.shadowRoot.querySelector(sel); }
    else { return null; }
  }
  return node;
};
"""
            return helper + "\nconst el = queryShadow('" + js_body.replace("'", "\\'") + "');\nif(el) el.click();"

        # If any candidate had found_shadow True, attach shadow guidance
        # Note: actual detection occurs server-side; here we just always include helper as optional guidance
        if True:
            if 'javascript' in snippets:
                snippets['javascript'] = wrap_shadow(snippets['javascript'])
            if 'typescript' in snippets:
                snippets['typescript'] = wrap_shadow(snippets['typescript'])
            # For other languages, add a comment explaining using JS executor
            for l in ('python','java','csharp'):
                if l in snippets:
                    snippets[l] = ("# If element is in shadow DOM, use JS execution to pierce shadow roots and return the element,\n# then interact with it. Example JS helper shown in JS/TS snippets.\n" + snippets[l])
        return snippets
