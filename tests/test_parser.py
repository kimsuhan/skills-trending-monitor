from src.crawler import parse_skill_items, _normalize_url


def test_normalize_relative_skill_url():
    assert _normalize_url("/obra/superpowers/abc", "https://skills.sh") == "https://skills.sh/obra/superpowers/abc"


def test_parse_from_embedded_json():
    html = '''
    <html><head>
    <script>
    self.__next_f.push([1,"16:[\"$\",\"$L1e\",null,{\"initialSkills\":[{\"source\":\"testorg/testrepo\",\"skillId\":\"hello\",\"name\":\"hello\",\"installs\":123}]}"])
    </script>
    </head><body></body></html>
    '''
    items = parse_skill_items(html)
    assert len(items) == 1
    assert items[0]["name"] == "hello"
    assert items[0]["category"] == "testorg/testrepo"
    assert items[0]["url"] == "https://skills.sh/testorg/testrepo/hello"
    assert items[0]["id_key"]


def test_parse_from_anchor_rows_fallback():
    html = '''
    <div>
      <a href="/org/skill/abc" class="item">
        <div><span>123</span></div>
        <div><h3>abc</h3><p>org/skill</p></div>
        <div>456</div>
      </a>
    </div>
    '''
    items = parse_skill_items(html)
    assert len(items) == 1
    assert items[0]["name"] == "abc"
    assert items[0]["category"] == "org/skill"
    assert items[0]["url"] == "https://skills.sh/org/skill/abc"
