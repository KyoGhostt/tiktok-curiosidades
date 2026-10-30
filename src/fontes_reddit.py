"""Teste (só leitura) da escolha de histórias: mostra o que story.pick_story() traria agora."""
import story
c = story.pick_story(6)
print("DEBUG:", " | ".join(story.DEBUG))
for p in c:
    print(f"- r/{p['sub']}/{p['kind']} pos {p['pos']} len {len(p['text'])} nota {story._nota(p):.1f} :: {p['title'][:90]}")
print("total candidatos:", len(c))
