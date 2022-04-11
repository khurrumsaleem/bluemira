# bluemira is an integrated inter-disciplinary design tool for future fusion
# reactors. It incorporates several modules, some of which rely on other
# codes, to carry out a range of typical conceptual fusion reactor design
# activities.
#
# Copyright (C) 2021 M. Coleman, J. Cook, F. Franza, I.A. Maione, S. McIntosh, J. Morris,
#                    D. Short
#
# bluemira is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# bluemira is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with bluemira; if not, see <https://www.gnu.org/licenses/>.

import pytest

from bluemira.base.components import Component, MagneticComponent, PhysicalComponent
from bluemira.base.error import ComponentError


class TestComponentClass:
    """
    Tests for the base Component functionality.
    """

    def test_tree(self):
        target_tree = """Parent (Component)
└── Child (Component)
    └── Grandchild (Component)"""

        child = Component("Child")
        parent = Component("Parent", children=[child])
        grandchild = Component("Grandchild", parent=child)
        assert parent.tree() == target_tree

        root: Component = grandchild.root
        assert root.tree() == target_tree

    def test_get_component_full_tree(self):
        parent = Component("Parent")
        child1 = Component("Child1", parent=parent)
        child2 = Component("Child2", parent=parent)
        grandchild = Component("Grandchild", parent=child1)

        assert grandchild.get_component("Child2", full_tree=True) is child2

    def test_get_component_from_node(self):
        parent = Component("Parent")
        child1 = Component("Child1", parent=parent)
        Component("Child2", parent=parent)
        grandchild = Component("Grandchild", parent=child1)

        assert grandchild.get_component("Child2") is None

    def test_get_component_multiple_full_tree(self):
        parent = Component("Parent")
        child1 = Component("Child", parent=parent)
        Component("Child", parent=parent)
        grandchild = Component("Grandchild", parent=child1)

        components = grandchild.get_component("Child", first=False, full_tree=True)
        assert len(components) == 2
        assert components[0] is not components[1]
        assert components[0].parent == components[1].parent

    def test_get_component_multiple_from_node(self):
        parent = Component("Parent")
        child1 = Component("Child", parent=parent)
        child2 = Component("Child", parent=parent)
        grandchild1 = Component("Grandchild", parent=child1)
        grandchild2 = Component("Grandchild", parent=child2)

        components = child1.get_component("Grandchild", first=False)
        assert len(components) == 1
        assert components[0] is grandchild1

        components = child2.get_component("Grandchild", first=False)
        assert len(components) == 1
        assert components[0] is grandchild2

    def test_get_component_missing(self):
        parent = Component("Parent")
        child = Component("Child", parent=parent)
        grandchild = Component("Grandchild", parent=child)

        component = grandchild.get_component("Banana")
        assert component is None

    def test_add_child(self):
        parent = Component("Parent")
        child = Component("Child")

        parent.add_child(child)
        assert parent.children == (child,)

    def test_fail_add_duplicate_child(self):
        parent = Component("Parent")
        child = Component("Child", parent=parent)

        with pytest.raises(ComponentError):
            parent.add_child(child)

    def test_add_children(self):
        parent = Component("Parent")
        child1 = Component("Child1")
        child2 = Component("Child2")

        parent.add_children([child1, child2])
        assert parent.children == (child1, child2)

    def test_add_children_given_tuple_of_components(self):
        parent = Component("Parent")
        children = (Component("Child1"), Component("Child2"))

        parent.add_children(children)

        assert [ch.name for ch in parent.children] == ["Child1", "Child2"]

    def test_add_children_does_nothing_given_empty_list(self):
        parent = Component("parent")

        parent.add_children([])

        assert len(parent.children) == 0

    def test_fail_add_duplicate_children(self):
        parent = Component("Parent")
        child1 = Component("Child1", parent=parent)
        child2 = Component("Child2")

        with pytest.raises(ComponentError):
            parent.add_children([child1, child2])

    def test_prune_child_removes_node_with_given_name(self):
        parent = Component("Parent")
        Component("Child1", parent=parent)
        Component("Child2", parent=parent)

        parent.prune_child("Child1")

        assert parent.get_component("Child1") is None
        assert parent.get_component("Child2") is not None

    def test_prune_child_does_nothing_if_node_does_not_exist(self):
        parent = Component("Parent")
        Component("Child1", parent=parent)

        parent.prune_child("not_a_child")

        assert parent.get_component("Child1") is not None

    def test_merge_children_merges_trees(self):
        parent_1 = _tree_from_dict({"parent_1": {"x": "leaf_1_x", "y": {"leaf_1_y"}}})
        parent_2 = _tree_from_dict({"parent_2": {"x": "leaf_2_x", "z": {"leaf_1_z"}}})

        parent_1.merge_children(parent_2)

        x_component = parent_1.get_component("x")
        assert isinstance(x_component, Component)
        assert [ch.name for ch in x_component.children] == ["leaf_1_x", "leaf_2_x"]
        y_component = parent_1.get_component("y")
        assert [ch.name for ch in y_component.children] == ["leaf_1_y"]
        z_component = parent_1.get_component("z")
        assert [ch.name for ch in z_component.children] == ["leaf_1_z"]

    def test_merge_children_given_2_shared_nodes(self):
        tree_1 = {"parent_1": {"x": "leaf_1_x", "y": "leaf_1_y"}}
        parent_1 = _tree_from_dict(tree_1)
        tree_2 = {"parent_2": {"x": "leaf_2_x", "y": "leaf_2_y"}}
        parent_2 = _tree_from_dict(tree_2)

        parent_1.merge_children(parent_2)

        x_component = parent_1.get_component("x")
        assert isinstance(x_component, Component)
        assert isinstance(x_component.get_component("leaf_1_x"), Component)
        assert isinstance(x_component.get_component("leaf_2_x"), Component)
        y_component = parent_1.get_component("y")
        assert isinstance(y_component, Component)
        assert isinstance(y_component.get_component("leaf_1_y"), Component)
        assert isinstance(y_component.get_component("leaf_2_y"), Component)

    def test_merge_children_given_shared_leaf(self):
        parent_1 = Component("parent_1")
        Component("x", parent=parent_1)
        parent_2 = Component("parent_2")
        Component("x", parent=parent_2)

        parent_1.merge_children(parent_2)

        assert len(parent_1.get_component("x", first=False)) == 1

    def test_merge_children_ComponentError_given_multiple_common_nodes(self):
        parent_1 = _tree_from_dict({"parent_1": {"x": {"x2": "leaf_1"}}})
        parent_2 = _tree_from_dict({"parent_2": {"x": {"x2", "leaf_2"}}})

        with pytest.raises(ComponentError):
            parent_1.merge_children(parent_2)

    def test_merge_children_does_not_merge_nodes_of_different_depth(self):
        parent_1 = _tree_from_dict({"parent_1": {"x": "leaf_1_x"}})
        parent_2 = _tree_from_dict({"parent_1": {"inter": {"x": "leaf_1_x"}}})

        parent_1.merge_children(parent_2)

        x_components = parent_1.get_component("x", first=False)
        assert len(x_components) == 2
        assert x_components[0].depth == 1
        assert x_components[1].depth == 2


class TestPhysicalComponent:
    """
    Tests for the PhysicalComponent class.
    """

    def test_shape(self):
        component = PhysicalComponent("Dummy", shape="A shape")
        assert component.shape == "A shape"

    def test_material_default(self):
        component = PhysicalComponent("Dummy", shape="A shape")
        assert component.material is None

    def test_material(self):
        component = PhysicalComponent("Dummy", shape="A shape", material="A material")
        assert component.material == "A material"


class TestMagneticComponent:
    """
    Tests for the MagneticComponent class.
    """

    def test_shape(self):
        component = MagneticComponent("Dummy", shape="A shape")
        assert component.shape == "A shape"

    def test_conductor_default(self):
        component = MagneticComponent("Dummy", shape="A shape")
        assert component.material is None

    def test_conductor(self):
        component = MagneticComponent("Dummy", shape="A shape", conductor="A conductor")
        assert component.conductor == "A conductor"


def _tree_from_dict(item, component_parent=None) -> Component:
    """
    Build a component tree from a dictionary.

    Defining larger component trees in a dictionary is far more
    readable than lines and lines of `add_child` calls.
    """
    for parent, children in item.items():
        component = Component(parent, parent=component_parent)
        if isinstance(children, dict):
            _tree_from_dict(children, component_parent=component)
        elif isinstance(children, str):
            component.add_child(Component(children))
        else:
            for child in children:
                component.add_child(Component(child))
    return component
