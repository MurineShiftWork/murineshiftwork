import yaml
from jinja2 import Template


def render_from_config(
    template_file: str = "template.html",
    config_file: str = "streams.yaml",
    site_file: str = "index.html",
):
    config = yaml.safe_load(open(config_file).read())
    template = Template(open(template_file).read())
    open(site_file, "w").write(template.render(groups=config))


if __name__ == "__main__":
    render_from_config()

"""
Run with:
    python -m http.server

-> Change streams.yaml to test camera configs
"""
