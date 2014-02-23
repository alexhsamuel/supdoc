from   collections import OrderedDict
from   inspect import Parameter, Signature

#------------------------------------------------------------------------------

class Record(type):

	class Base:

		def __init__(self, *args, **kw_args):
			bound = self.__signature__.bind(*args, **kw_args)

			for name, (type, default) in self.__fields__.items():
				try:
					value = bound.arguments[name]
				except KeyError:
					value = default
				else:
					try:
						value = type(value)
					except Exception as exc:
						raise TypeError(
							"can't convert {!r} to {} for {}"
							.format(value, type.__name__, name)) from exc
				setattr(self, name, value)


		def __repr__(self):
			return "{}({})".format(
				self.__class__.__name__, 
				", ".join( "{}={!r}".format(
					n, getattr(self, n)) for n in self.__fields__ ))


		def __setattr__(self, name, value):
			try:
				type, _ = self.__fields__[name]
			except KeyError:
				raise AttributeError("no field {}".format(name))
			else:
				try:
					value = type(value)
				except Exception as exc:
					raise TypeError(
						"can't convert {!r} to {} for {}"
						.format(value, type.__name__, name)) from exc
			super().__setattr__(name, value)


	@classmethod
	def __prepare__(metaclass, name, bases):
		return OrderedDict()


	def __new__(metaclass, name, bases, dict):
		# FIXME: Support subclassing records.
		if len(bases) > 0:
			raise TypeError("a Record cannnot have base classes")
		bases = (metaclass.Base, )
		fields = OrderedDict( 
			(n, (type(v), v)) 
			for n, v in dict.items() 
			if not n.startswith("_")
			)
		signature = Signature([ 
			Parameter(n, Parameter.POSITIONAL_OR_KEYWORD, default=d)
			for n, (_, d) in fields.items() 
			])

		obj = type.__new__(metaclass, name, bases, dict)
		obj.__fields__ = fields
		obj.__signature__ = signature
		obj.__slots__ = tuple(fields)

		return obj


	def __init__(self, *args, **kw_args):
		pass



class Stat(metaclass=Record):
	st_mtime = int()
	st_size = int()
	st_path = str()



if __name__ == "__main__":
	s = Stat(st_size=1024)
	print(s)

