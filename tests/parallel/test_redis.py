# pylint: disable=unused-argument
from __future__ import annotations

# Standard Library Imports
import os
import pickle

# Third Party Imports
import pytest
from redis import Redis
from redis import exceptions as redis_exceptions

# RESONAATE Imports
from resonaate.parallel import (
    RedisConfig,
    getMasterHash,
    getRedisConnection,
    isMaster,
    masterExists,
    resetMaster,
    resetRedisQueue,
    setUpLogger,
)


class TestRedis:
    """Tests defining interface with Redis library."""

    def testRedisConfig(self, monkeypatch):
        """Test all functionality of the _RedisConfig class."""
        hostname = "localhost"
        port = 7777
        password = "test_password"

        # Empty config, use defaults (password from environment variables)
        envs = {"REDIS_PASSWORD": password}
        with monkeypatch.context() as m_patch:
            # Limit scope of env variable
            m_patch.setattr(os, "environ", envs)
            redis_config = RedisConfig()
            assert redis_config.redis_password == password

        # Set defaults
        redis_config.setDefaultConnectionParameters(hostname, port, password)
        assert redis_config.redis_hostname == hostname
        assert redis_config.redis_port == port
        assert redis_config.redis_password == password

        # Set defaults with bad values
        with pytest.raises(TypeError):
            redis_config.setDefaultConnectionParameters(444323, port, password)

        with pytest.raises(TypeError):
            redis_config.setDefaultConnectionParameters(hostname, "7777", password)

        with pytest.raises(TypeError):
            redis_config.setDefaultConnectionParameters(hostname, port, 324343)

        # Test getConfig() class method
        new_config = RedisConfig.getConfig()
        assert new_config is not redis_config
        assert new_config is RedisConfig.getConfig()

    def testGetRedisConnection(self):
        """Test Redis factory method."""
        redis_instance = getRedisConnection()
        assert redis_instance is not None
        assert redis_instance is getRedisConnection()

    def testResetRedisQueue(self, redis):
        """Test resetting a redis queue."""
        queue_name = "custom_queue_name"
        redis.rpush(queue_name, pickle.dumps("test_val_0"))
        redis.rpush(queue_name, pickle.dumps("test_val_1"))
        assert resetRedisQueue(redis, queue_name) == 2

    def testIsMaster(self, redis):
        """Test setting the master redis key."""
        # Call with explicit redis instance
        assert isMaster(redis_connection=redis) is True
        # Call with implicit redis instance
        assert isMaster() is True
        # Call an catch a connection error because of malformed hostname
        with pytest.raises(redis_exceptions.ConnectionError):
            isMaster(redis_connection=Redis(host="local"))

    def testMasterExists(self, redis):
        """Test checking the master redis key is set."""
        # Call with explicit redis instance
        assert masterExists(redis_connection=redis) is True
        # Call with implicit redis instance, master key unset
        resetMaster()
        assert masterExists() is False

    def testResetMaster(self, redis):
        """Test resetting the master redis key."""
        # Call with explicit redis instance
        assert resetMaster(redis_connection=redis) is True
        assert masterExists(redis_connection=redis) is False
        # Call with implicit redis instance, master key unset
        assert masterExists() is False
        assert resetMaster() is False

    def testGetMasterHash(self, redis):
        """Test getting the master hash attribute."""
        assert getMasterHash() is not None

    def testSetupLogger(self):
        """Test getting the master hash attribute."""
        # assert REDIS_QUEUE_LOGGER.hasHandlers() is False
        setUpLogger()
