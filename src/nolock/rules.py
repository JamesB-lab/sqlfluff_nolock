"""A custom rule to check for NOLOCK implemented through the plugin system.

This uses the rules API supported from 2.0.0 onwards.
"""

import os.path
from typing import Tuple, List, Type

from sqlfluff.core.plugin import hookimpl
from sqlfluff.core.config import ConfigLoader
from sqlfluff.core.rules import (
    BaseRule,
    LintFix,
    LintResult,
    RuleContext,
)
from sqlfluff.core.rules.crawlers import SegmentSeekerCrawler
from sqlfluff.utils.functional import (
    FunctionalContext,
    sp,
)
from sqlfluff.core.parser import (
    BaseSegment,
    RawSegment,
)
from sqlfluff.dialects.dialect_tsql import (
    TableHintSegment,
)

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

    def _eval(self, context: RuleContext):
        """We should not lock the table when selecting."""
        assert context.segment.is_type("from_expression_element")
        if self._lint(context):
            return None
        # self.print_tree(context.segment, 0)
        fixes = self._fixes(context)
        return LintResult(
            anchor = context.segment,
            description = "Missing table hint NOLOCK",
            fixes = fixes
        )

    def _lint(self, context: RuleContext)->bool:
        from_expression_element = FunctionalContext(context).segment
        matches = from_expression_element.children(sp.is_type("post_table_expression")) \
            .children(sp.is_type('bracketed')) \
            .children(sp.is_type('query_hint_segment')) \
            .children(sp.is_type('keyword'))
        if len(matches) > 0:
            keyword = matches[0]
            if keyword.raw == 'NOLOCK':
                return True
        matches = from_expression_element.children(sp.is_type("alias_expression")) \
            .children(sp.is_type('bracketed')) \
            .children(sp.is_type('identifier_list')) \
            .children(sp.is_type('naked_identifier'))
        if len(matches) > 0:
            keyword = matches[0]
            if keyword.raw == 'NOLOCK':
                return True
        return False
    
    def _fixes(self, context: RuleContext)->Tuple[Type[LintFix]]:
        tablename = context.segment.get_raw_segments()[0].raw
        return [
            LintFix.replace(
                context.segment, [
                    RawSegment(f'{tablename} WITH (NOLOCK)'),
                ]
            )
        ]

    def print_tree(self, segment: BaseSegment, level: int):
        for childseg in segment.segments:
            print(f'{level}: {" "*level*2}{childseg} | {childseg.type}')
            self.print_tree(childseg, level + 1)