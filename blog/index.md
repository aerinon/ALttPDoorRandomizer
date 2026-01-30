---
layout: default
title: Blog
nav_order: 6
has_children: false
---

# Development Blog
{: .no_toc }

Latest updates, release notes, and development insights for ALttP Door Randomizer.
{: .fs-6 .fw-300 }

---

## Recent Posts

{% assign posts = site.posts | sort: 'date' | reverse %}
{% for post in posts limit:10 %}
<div class="post-entry" style="margin-bottom: 2em; padding-bottom: 1em; border-bottom: 1px solid #eeebee;">
  <h3 style="margin-bottom: 0.5em;">
    <a href="{{ post.url | relative_url }}">{{ post.title }}</a>
  </h3>
  <p style="color: #5C5962; font-size: 0.9em; margin-bottom: 0.5em;">
    {{ post.date | date: "%B %d, %Y" }}
    {% if post.author %} • by {{ post.author }}{% endif %}
  </p>
  <p>{{ post.excerpt | strip_html | truncatewords: 50 }}</p>
  <p><a href="{{ post.url | relative_url }}">Read more →</a></p>
</div>
{% endfor %}

---

## Categories

Browse posts by category:

- [Release Notes](#release-notes)
- [Development Updates](#development-updates)
- [Feature Highlights](#feature-highlights)
- [Technical Deep Dives](#technical-deep-dives)

### Release Notes

{% assign release_posts = site.posts | where: "category", "release" %}
{% for post in release_posts limit:5 %}
- [{{ post.title }}]({{ post.url | relative_url }}) - {{ post.date | date: "%B %d, %Y" }}
{% endfor %}

### Development Updates

{% assign dev_posts = site.posts | where: "category", "development" %}
{% for post in dev_posts limit:5 %}
- [{{ post.title }}]({{ post.url | relative_url }}) - {{ post.date | date: "%B %d, %Y" }}
{% endfor %}

### Feature Highlights

{% assign feature_posts = site.posts | where: "category", "features" %}
{% for post in feature_posts limit:5 %}
- [{{ post.title }}]({{ post.url | relative_url }}) - {{ post.date | date: "%B %d, %Y" }}
{% endfor %}

### Technical Deep Dives

{% assign feature_posts = site.posts | where: "category", "features" %}
{% for post in feature_posts limit:5 %}
- [{{ post.title }}]({{ post.url | relative_url }}) - {{ post.date | date: "%B %d, %Y" }}
  {% endfor %}

---

## Subscribe

Stay up to date with Door Randomizer development:

- **Discord**: Join [ALTTP Randomizer Discord](https://discordapp.com/invite/alttprandomizer) in `#door-rando`

---

## Archive

View all posts by year:

{% assign posts_by_year = site.posts | group_by_exp: "post", "post.date | date: '%Y'" %}
{% for year in posts_by_year %}
### {{ year.name }}
{% for post in year.items %}
- [{{ post.title }}]({{ post.url | relative_url }}) - {{ post.date | date: "%B %d, %Y" }}
{% endfor %}
{% endfor %}

---

## Contributing to the Blog

Want to write a guest post or contribute content?

Contact us on Discord to discuss your ideas!
