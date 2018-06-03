% include("header")
	      <div class="jumbotron">
	        <h1>Leaks</h1>
	        <p class="lead">List of the different aggregated leaks/files in the database.<br/>
	        	<b style="color:red;">{{count}}</b> credentials indexed.</p>
	      </div>
	      % if leaks != None :
	      	<b style="color:red;">{{nbLeaks}} indexed leaks</b>

		      <table class="table-striped table table-hover">
				<tr>
					<th>Name</th>
					<th>Number of credentials</th>
					<th>File</th>
					<th>Remove</th>
				</tr>
				% for l in leaks :
				<tr>
					<td>{{l["name"]}}</td>
					<td>{{l["imported"]}}</td>
					<td>{{l["filename"]}}</td>
					<td><b><a style="color:red;text-decoration:none;" href="/removeLeak?id={{l["id"]}}">X</a></b></td>
				</tr>
				% end
			</table>
		% end
		<div class="row-fluid addLeaks">
			<h5>How to add leaks</h5>
			<p>Use the <i><b>leakStandardizer</b></i> and <i><b>leakImporter</b></i> scripts to add leaks. <i><b>leakStandardizer</b></i> helps getting a uniformed leak file following a defined format (email:hash:plain) out of a file full of junk (your initial leak obtained from a spooky place on the Internet). The <i><b>leakImporter</b></i> scripts will parse this file, convert it into a CSV and import it in your mongo/mysql database faster than speed !</p>
		</div>
% include("footer")