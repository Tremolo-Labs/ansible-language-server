"""Magic variables - auto-generated from Ansible source.

DO NOT EDIT. Regenerate with: python tools/extract_schema.py
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MagicVariable:
    """An Ansible magic variable."""
    name: str
    scope: str
    description: str = ""


MAGIC_VARS: dict[str, MagicVariable] = {
    'ansible_become': MagicVariable('ansible_become', 'task', 'Whether privilege escalation is enabled'),
    'ansible_become_method': MagicVariable('ansible_become_method', 'task', 'Privilege escalation method (sudo, su, etc.)'),
    'ansible_become_user': MagicVariable('ansible_become_user', 'task', 'User to escalate to'),
    'ansible_check_mode': MagicVariable('ansible_check_mode', 'play', 'True if running in check mode'),
    'ansible_config_file': MagicVariable('ansible_config_file', 'global', 'Path to ansible.cfg in use'),
    'ansible_connection': MagicVariable('ansible_connection', 'host', 'Connection plugin name'),
    'ansible_diff_mode': MagicVariable('ansible_diff_mode', 'play', 'True if running in diff mode'),
    'ansible_facts': MagicVariable('ansible_facts', 'host', 'Facts gathered for the host'),
    'ansible_host': MagicVariable('ansible_host', 'host', 'Target host address'),
    'ansible_index_var': MagicVariable('ansible_index_var', 'loop', 'Name of loop index variable'),
    'ansible_local': MagicVariable('ansible_local', 'host', 'Local facts from /etc/ansible/facts.d'),
    'ansible_loop': MagicVariable('ansible_loop', 'loop', 'Extended loop info (index, first, last, etc.)'),
    'ansible_loop_var': MagicVariable('ansible_loop_var', 'loop', 'Name of the loop variable'),
    'ansible_play_batch': MagicVariable('ansible_play_batch', 'play', 'Hosts in current batch (serial)'),
    'ansible_play_hosts': MagicVariable('ansible_play_hosts', 'play', 'Same as play_hosts'),
    'ansible_play_hosts_all': MagicVariable('ansible_play_hosts_all', 'play', 'All hosts in play, even failed'),
    'ansible_play_name': MagicVariable('ansible_play_name', 'play', 'Name of the current play'),
    'ansible_port': MagicVariable('ansible_port', 'host', 'Target connection port'),
    'ansible_role_name': MagicVariable('ansible_role_name', 'role', 'Name of currently executing role'),
    'ansible_ssh_private_key_file': MagicVariable('ansible_ssh_private_key_file', 'host', 'SSH private key file path'),
    'ansible_user': MagicVariable('ansible_user', 'host', 'Target user for connection'),
    'ansible_verbosity': MagicVariable('ansible_verbosity', 'play', 'Current verbosity level'),
    'ansible_version': MagicVariable('ansible_version', 'global', 'Dict with Ansible version info'),
    'group_names': MagicVariable('group_names', 'host', 'List of groups the host belongs to'),
    'groups': MagicVariable('groups', 'global', 'Dict of all groups and their hosts'),
    'hostvars': MagicVariable('hostvars', 'global', 'Dict of all host variables'),
    'inventory_dir': MagicVariable('inventory_dir', 'global', 'Directory containing the inventory file'),
    'inventory_file': MagicVariable('inventory_file', 'global', 'Path to the inventory file'),
    'inventory_hostname': MagicVariable('inventory_hostname', 'host', 'Full hostname from inventory'),
    'inventory_hostname_short': MagicVariable('inventory_hostname_short', 'host', 'Short hostname (before first dot)'),
    'item': MagicVariable('item', 'loop', 'Current loop item'),
    'play_hosts': MagicVariable('play_hosts', 'play', 'List of hosts in current play'),
    'playbook_dir': MagicVariable('playbook_dir', 'global', 'Directory containing the playbook'),
    'role_name': MagicVariable('role_name', 'role', 'Same as ansible_role_name'),
    'role_path': MagicVariable('role_path', 'role', 'Path to current role directory'),
}

MAGIC_VAR_NAMES: frozenset[str] = frozenset(MAGIC_VARS.keys())


def is_magic_variable(name: str) -> bool:
    return name in MAGIC_VAR_NAMES
