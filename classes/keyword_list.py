from .keyword import Keyword

class KeywordList:
	def __init__(self, keywords):
		self.keywords= keywords

	def __iter__(self):
		return (x for x in self.keywords)

	def __getitem__(self, key):
		for x in self.keywords:
			if key.lower() in [x.name] + x.aliases:
				return x

	def __contains__(self, item):
		for x in self.keywords:
			if isinstance(item,str) and item.lower() in [x.name] + x.aliases:
				return True
			if isinstance(item, Keyword) and item in self.keywords:
				return True
		return False

	def __delitem__(self, instance):
		for x in self.keywords:
			if x.name == instance:
				tmp= x
				break
		else: return
		self.keywords.remove(tmp)

	def to_query(self):
		ret= []

		has_val= [x for x in self.keywords if x.has_value]
		for x in has_val:
			ret.append(f"{x.name.lower()}" if isinstance(x,bool) else f"{x.name.lower()}{str(x.value).upper()}")

		return " ".join(ret)

	def values(self):
		return [x.value for x in self.keywords]