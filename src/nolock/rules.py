"""A custom rule to check for NOLOCK implemented through the plugin system.

This uses the rules API supported from 2.0.0 onwards.
"""

from sqlfluff.core.plugin import hookimpl
from sqlfluff.core.rules import (
    BaseRule,
    LintFix,
    LintResult,
    RuleContext,
)
from sqlfluff.core.rules.crawlers import SegmentSeekerCrawler
from typing import List, Type
import os.path
from sqlfluff.core.config import ConfigLoader
from sqlfluff.utils.functional import FunctionalContext, sp
from sqlfluff.core.parser import NewlineSegment, WhitespaceSegment, RawSegment, Bracketed, KeywordSegment

@hookimpl
def get_rules() -> List[Type[BaseRule]]:
    """Get plugin rules."""
    return [Rule_NOLOCK_L001]


@hookimpl
def load_default_config() -> dict:
    """Loads the default configuration for the plugin."""
    return ConfigLoader.get_global().load_config_file(
        file_dir=os.path.dirname(__file__),
        file_name="plugin_default_config.cfg",
    )


@hookimpl
def get_configs_info() -> dict:
    """Get rule config validations and descriptions."""
    return {
        "check_from": {"definition": "Flag to check FROM clauses"},
        "check_join": {"definition": "Flag to check JOIN clauses"},
    }


# These two decorators allow plugins
# to be displayed in the sqlfluff docs
class Rule_NOLOCK_L001(BaseRule):
    """Locking tables is forbidden

    **Anti-pattern**

    Not using `WITH (NOLOCK)` when accessing a table

    .. code-block:: sql

        SELECT mytable.mycol
        FROM mytable
        LEFT JOIN othertable ON mytable.id = othertable.id
        ORDER BY mytable.mycol;

    **Best practice**

    Ensure the table isn't locked.

    .. code-block:: sql

        SELECT mytable.mycol
        FROM mytable WITH (NOLOCK)
        LEFT JOIN othertable WITH (NOLOCK) ON mytable.id = othertable.id
        ORDER BY mytable.mycol;
    """

    groups = ("all",)
    config_keywords = ["check_from","check_join"]
    crawl_behaviour = SegmentSeekerCrawler({"from_expression_element"})
    is_fix_compatible = True

    def __init__(self, *args, **kwargs):
        """Overwrite __init__ to set config."""
        super().__init__(*args, **kwargs)
        self.check_from = self.check_from
        self.check_join = self.check_join
        self.is_fixed = False
        self.give_up = 0

    def _eval(self, context: RuleContext):
        """We should not lock the table when selecting."""
        assert context.segment.is_type("from_expression_element")

        from_expression_element = FunctionalContext(context).segment
        matches = from_expression_element.children(sp.is_type("post_table_expression")) \
            .children(sp.is_type('bracketed')) \
            .children(sp.is_type('query_hint_segment')) \
            .children(sp.is_type('keyword'))
        if len(matches) > 0:
            keyword = matches[0]
            if keyword.raw == 'NOLOCK':
                return None
            print(keyword.raw)
        matches = from_expression_element.children(sp.is_type("alias_expression")) \
            .children(sp.is_type('bracketed')) \
            .children(sp.is_type('identifier_list')) \
            .children(sp.is_type('naked_identifier'))
        if len(matches) > 0:
            keyword = matches[0]
            if keyword.raw == 'NOLOCK':
                return None
        # if self.give_up < 4:
        #     return None
        self.give_up += 1
        return LintResult(
            anchor = context.segment,
            description = "Missing table hint NOLOCK",
            fixes = [
                LintFix.create_after(
                    anchor_segment = context.segment,
                    edit_segments = [
                        WhitespaceSegment(),
                        RawSegment("WITH (NOLOCK)"),
                    ],
                )
            ],
        )

def print_tree(segment, level):
    for childseg in segment.segments:
        print(f'{level}: {" "*level*2}{childseg} | {childseg.type}')
        print_tree(childseg, level + 1)