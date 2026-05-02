import warnings

# Ensure a DB driver is available in environments where compiling mysqlclient
# is not possible (e.g., some managed buildpacks). Prefer native MySQLdb
# (mysqlclient) when available, otherwise fall back to PyMySQL.
try:
	import MySQLdb  # noqa: F401
except Exception:
	try:
		import pymysql

		pymysql.install_as_MySQLdb()
		warnings.warn("Using PyMySQL as MySQLdb fallback; for best performance install mysqlclient.")
	except Exception:
		# Let Django raise the appropriate error later if no driver exists.
		warnings.warn("No MySQL driver available; please install mysqlclient or PyMySQL.")
