% include("header")

	      <!-- Jumbotron -->
	      <div class="jumbotron">
	        <h1>Lookup</h1>
	        <p class="lead">Search within <b style="color: red;"">{{count}} credentials</b> in the database.</p>
			<form method="GET" action="/">
				<p><input type="text" style="width:100%;height:60px;font-size:25px;" name="search" value="{{query}}" autofocus/></p>
				<p><input type="submit" value="Submit" role="buttont" class="btn btn-lg btn-success"/></p>
			</form>
	      </div>
	      % if creds != None :
	      	<b style="color:red;">
	      		% if display_more :
	      		  More than
	      		%end
	      	{{nbRes+((numPage-1)*max_pages*step)}} results</b>

	      	<select name="step" id="step" onchange="document.location='/?search={{query}}&step='+document.getElementById('step').value;">
	      		% if step == 500 :
	      			<option value="500" selected="selected">500</option>
	      		% else :
	      			<option value="500">500</option>
	      		% end
	      		% if step == 1000 :
	      			<option value="1000" selected="selected">1000</option>
	      		% else :
	      			<option value="1000">1000</option>
	      		% end
	      		% if step == 2000 :
	      			<option value="2000" selected="selected">2000</option>
	      		% else :
	      			<option value="2000">2000</option>
	      		% end
	      		% if step == 5000 :
	      			<option value="5000" selected="selected">5000</option>
	      		% else :
	      			<option value="5000">5000</option>
	      		% end
	      	</select>
	      	  % if display_less :
	      	  <a href="/?search={{query}}&page={{first_page-1}}&numPage={{numPage-1}}">(-)</a>
	      	  % end
	      	  % for i in range(first_page,first_page+nbPages) :
	      	  % if i == page :
	      	  	<b><i>
	      	  % end
	      	  <a href="/?search={{query}}&page={{i}}&numPage={{numPage}}">{{i}}</a>
	      	  % if i == page :
	      	  	</i></b>
	      	  % end
	      	  % end
	      	  % if display_more :
	      	  <a href="/?search={{query}}&page={{(numPage*max_pages)+1}}&numPage={{numPage+1}}">(+)</a>
	      	  % end
	      	  <p style="float:right;">
	      	  	Export
	      	  	<a class="btn btn-primary" href="/export?search={{query}}&what=all" role="button">All</a>
	      	  	<a class="btn btn-primary" href="/export?search={{query}}&what=left" role="button">Left</a>
	      	  	<a class="btn btn-primary" href="/export?search={{query}}&what=cracked" role="button">Cracked</a>
	      	  </p>
		      <table class="table-striped table table-hover">
				<tr>
					<th><label>Email <input id="chk_email" type="checkbox" unchecked onclick="switchsafemode('email');"/></label></th>
					<th><label>Hash <input id="chk_hash" type="checkbox" unchecked onclick="switchsafemode('hash');"/></label></th>
					<th><label>Plain <input id="chk_plain" type="checkbox" unchecked onclick="switchsafemode('plain');"/></label></th>
				</tr>
				% for c in creds :
				<tr>
					<td><span class="email">{{c["p"]}}</span>@{{c["d"]}}</td>
					<td><span class="hash">{{c["h"]}}</span></td>
					<td><span class="plain">{{c["P"]}}</span></td>
				</tr>
				% end
			</table>
		% end
% include("footer")