---
title: Languages
icon: fas fa-language
order: 4
---

모든 기술 포스트는 한국어 원문과 일본어·영어·프랑스어·독일어 번역으로 제공합니다. 각 글 상단의 언어 전환 메뉴를 사용하면 같은 내용을 바로 비교할 수 있습니다.

{% for language in site.data.languages %}
  {% assign localized_posts = site.posts | where: "lang", language.code %}
- [{{ language.label }}]({{ '/languages/' | append: language.slug | append: '/' | relative_url }}) — {{ localized_posts.size }} posts
{% endfor %}
