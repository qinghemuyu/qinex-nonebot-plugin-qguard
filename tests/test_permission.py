from nonebot_plugin_qguard.enums import QGuardRole


def test_permission_role_order() -> None:
    assert QGuardRole.SUPER_ADMIN > QGuardRole.GROUP_OWNER
    assert QGuardRole.GROUP_OWNER > QGuardRole.GROUP_ADMIN
    assert QGuardRole.GROUP_ADMIN > QGuardRole.MINI_ADMIN
    assert QGuardRole.MINI_ADMIN > QGuardRole.TRUSTED
    assert QGuardRole.TRUSTED > QGuardRole.MEMBER
